"""
FinanceDataReader를 사용한 분봉 데이터 수집
네이버 API 대신 안정적인 과거 데이터 제공
"""
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


class FDRMinuteFetcher:
    """FinanceDataReader 기반 분봉 크롤러"""
    
    def __init__(self):
        self.cache = {}
    
    def fetch_historical_data(self, stock_code, stock_name='', timeframe='1', days_back=730):
        """
        과거 일봉 데이터 수집 후 분봉으로 변환 시뮬레이션
        
        Note: FDR은 분봉을 제공하지 않으므로, 일봉 데이터를 수집합니다.
        실제 분봉이 필요하면 KIS API 등 유료 서비스 필요
        
        Args:
            stock_code (str): 종목코드
            stock_name (str): 종목명
            timeframe (str): '1' (무시됨, 일봉만 제공)
            days_back (int): 수집 기간 (일)
        
        Returns:
            pd.DataFrame: OHLCV 데이터
        """
        print(f"[{stock_code} {stock_name}] 일봉 데이터 수집 중 (FDR)...")
        
        try:
            # 시작/종료 날짜 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # 일봉 데이터 수집
            df = fdr.DataReader(
                stock_code, 
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d')
            )
            
            if df is None or df.empty:
                print(f"[{stock_code}] 데이터 없음")
                return None
            
            # 컬럼명 통일
            df = df.reset_index()
            df = df.rename(columns={
                'Date': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # 필요한 컬럼만 선택
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            df = df[required_cols]
            
            # timestamp를 datetime으로 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            print(f"[{stock_code}] {len(df)}개 일봉 수집 완료 ({df['timestamp'].min().date()} ~ {df['timestamp'].max().date()})\n")
            
            return df
            
        except Exception as e:
            print(f"[{stock_code}] 수집 오류: {e}")
            return None
    
    def save_to_csv(self, df, stock_code, timeframe='1', output_dir='./data/raw'):
        """데이터 저장"""
        import os
        
        # 절대 경로로 변환
        if not os.path.isabs(output_dir):
            output_dir = os.path.abspath(output_dir)
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 일봉이지만 기존 파이프라인과 호환을 위해 1min으로 저장
        filename = f"{stock_code}_1min.csv"
        filepath = f"{output_dir}/{filename}"
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"저장 완료: {filepath}")


def main():
    """테스트"""
    fetcher = FDRMinuteFetcher()
    
    # 삼성전자 테스트
    df = fetcher.fetch_historical_data('005930', '삼성전자', days_back=30)
    
    if df is not None:
        fetcher.save_to_csv(df, '005930')
        print("\n=== 데이터 미리보기 ===")
        print(df.head())
        print(df.tail())
        print(f"\n총 {len(df)}개 행")


if __name__ == '__main__':
    main()
