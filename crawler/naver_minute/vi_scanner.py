"""
VI 스캐너: 최근 데이터로 VI 발생 종목 탐지
"""
import pandas as pd
from .fdr_minute_fetcher import FDRMinuteFetcher
import time


class VIScanner:
    """VI 발생 가능성 높은 종목 스캔"""
    
    def __init__(self):
        self.fetcher = FDRMinuteFetcher()
    
    def quick_scan(self, stock_code, stock_name, scan_days=30):
        """
        빠른 VI 패턴 스캔 (최근 30일)
        
        Args:
            stock_code (str): 종목코드
            stock_name (str): 종목명
            scan_days (int): 스캔 기간
            
        Returns:
            dict: {'has_vi': bool, 'vi_count': int, 'stock_code': str}
        """
        try:
            df = self.fetcher.fetch_historical_data(
                stock_code, 
                stock_name, 
                timeframe='1', 
                days_back=scan_days
            )
            
            if df is None or len(df) == 0:
                return {'has_vi': False, 'vi_count': 0, 'stock_code': stock_code}
            
            # 간단한 VI 패턴 탐지
            vi_count = self._detect_vi_patterns(df)
            
            return {
                'has_vi': vi_count > 0,
                'vi_count': vi_count,
                'stock_code': stock_code,
                'stock_name': stock_name
            }
            
        except Exception as e:
            print(f"[{stock_code}] 스캔 오류: {e}")
            return {'has_vi': False, 'vi_count': 0, 'stock_code': stock_code}
    
    def _detect_vi_patterns(self, df):
        """
        간단한 VI 패턴 탐지 (빠른 스캔용)
        일봉 기준으로 변동성이 큰 종목 탐지
        
        Returns:
            int: 발견된 VI 패턴 수 (변동성 점수)
        """
        if df is None or len(df) < 5:
            return 0
        
        vi_count = 0
        
        # 일간 변동률 계산
        df['price_change'] = df['close'].pct_change()
        df['daily_range'] = (df['high'] - df['low']) / df['low']
        
        # 5% 이상 급등/급락 일수
        extreme_moves = df[abs(df['price_change']) > 0.05]
        vi_count += len(extreme_moves) * 2  # 가중치 2배
        
        # 일중 변동폭 7% 이상 (VI 가능성 높음)
        high_volatility = df[df['daily_range'] > 0.07]
        vi_count += len(high_volatility)
        
        # 거래량 급증 (평균 대비 3배 이상)
        if len(df) > 5:
            avg_volume = df['volume'].mean()
            volume_spikes = df[df['volume'] > avg_volume * 3]
            vi_count += len(volume_spikes)
        
        return min(vi_count, 20)  # 최대 20점
    
    def scan_all_stocks(self, stocks, scan_days=30, delay=1.0):
        """
        전체 종목 스캔
        
        Args:
            stocks (list): 종목 리스트 [{'종목코드': '', '종목명': ''}]
            scan_days (int): 스캔 기간
            delay (float): 종목 간 딜레이
            
        Returns:
            list: VI 발견 종목 리스트
        """
        from tqdm import tqdm
        
        vi_stocks = []
        
        print(f"\n{'='*60}")
        print(f"VI 스캔 시작: {len(stocks)}개 종목, 최근 {scan_days}일")
        print(f"{'='*60}\n")
        
        for stock in tqdm(stocks, desc="VI 스캔 진행"):
            result = self.quick_scan(
                stock['종목코드'], 
                stock['종목명'], 
                scan_days
            )
            
            if result['has_vi']:
                vi_stocks.append(result)
                print(f"[발견] {result['stock_code']} {result['stock_name']}: VI 패턴 {result['vi_count']}개")
            
            time.sleep(delay)
        
        print(f"\n{'='*60}")
        print(f"VI 스캔 완료: {len(vi_stocks)}개 종목에서 VI 패턴 발견")
        print(f"{'='*60}\n")
        
        return vi_stocks
    
    def save_vi_stocks(self, vi_stocks, output_path='./data/raw/vi_stocks.json'):
        """VI 발견 종목 저장"""
        import json
        from pathlib import Path
        from datetime import datetime
        import os
        
        # 절대 경로로 변환
        if not os.path.isabs(output_path):
            output_path = os.path.abspath(output_path)
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_count': len(vi_stocks),
            'stocks': vi_stocks
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"VI 종목 리스트 저장: {output_path}")
        return output_path


def main():
    """테스트"""
    import json
    
    # 종목 리스트 로드
    with open('../../data/raw/stock_list.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 테스트: 상위 20개만
    stocks = data['stocks'][:20]
    
    scanner = VIScanner()
    vi_stocks = scanner.scan_all_stocks(stocks, scan_days=30)
    scanner.save_vi_stocks(vi_stocks)


if __name__ == '__main__':
    main()
