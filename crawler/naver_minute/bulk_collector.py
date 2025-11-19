"""
전체 종목 분봉 데이터 일괄 수집 모듈
stock_list.json을 읽어서 전체 종목의 분봉 데이터를 수집합니다.
"""
import json
import pandas as pd
from pathlib import Path
import time
from tqdm import tqdm
from .fetch_minute_data import NaverMinuteFetcher


class BulkMinuteCollector:
    """전체 종목 분봉 일괄 수집"""
    
    def __init__(self, stock_list_path='../../data/raw/stock_list.json'):
        self.stock_list_path = stock_list_path
        self.fetcher = NaverMinuteFetcher()
        
    def load_stock_list(self, path=None):
        """종목 리스트 로드"""
        list_path = path if path else self.stock_list_path
        
        # JSON 또는 CSV 자동 감지
        if list_path.endswith('.json'):
            with open(list_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            stocks = data['stocks']
        else:  # CSV
            df = pd.read_csv(list_path, encoding='utf-8-sig')
            stocks = df.to_dict('records')
        
        print(f"총 {len(stocks)}개 종목 로드")
        return stocks
    
    def collect_all(self, timeframe='1', days_back=730, output_dir='../../data/raw', 
                    limit=None, delay=1.0, stock_list_path=None):
        """
        전체 종목 분봉 데이터 수집
        
        Args:
            timeframe (str): '1' 또는 '3'
            days_back (int): 수집 기간 (일)
            output_dir (str): 저장 디렉토리
            limit (int): 수집할 종목 수 제한 (테스트용, None=전체)
            delay (float): 종목 간 대기 시간 (초)
            stock_list_path (str): 종목 리스트 경로 (None이면 기본값 사용)
        """
        stocks = self.load_stock_list(stock_list_path)
        
        if limit:
            stocks = stocks[:limit]
            print(f"테스트 모드: {limit}개 종목만 수집")
        
        success_count = 0
        fail_count = 0
        
        print(f"\n{'='*60}")
        print(f"분봉 데이터 일괄 수집 시작")
        print(f"타임프레임: {timeframe}분봉, 기간: {days_back}일")
        print(f"{'='*60}\n")
        
        for stock in tqdm(stocks, desc="종목 수집 진행"):
            code = stock['종목코드']
            name = stock['종목명']
            
            try:
                # 분봉 데이터 수집
                df = self.fetcher.fetch_historical_data(
                    code, name, timeframe=timeframe, days_back=days_back
                )
                
                if df is not None and len(df) > 0:
                    # CSV 저장
                    self.fetcher.save_to_csv(df, code, timeframe, output_dir)
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"[SKIP] {code} {name}: 데이터 없음")
                
                # 서버 부하 방지
                time.sleep(delay)
                
            except Exception as e:
                fail_count += 1
                print(f"[ERROR] {code} {name}: {e}")
        
        print(f"\n{'='*60}")
        print(f"수집 완료: 성공 {success_count}개, 실패 {fail_count}개")
        print(f"{'='*60}")


def main():
    """메인 실행"""
    collector = BulkMinuteCollector()
    
    # 테스트: 10개 종목만 1분봉 30일치 수집
    collector.collect_all(
        timeframe='1',
        days_back=30,
        limit=10,  # 테스트용
        delay=1.0
    )
    
    # 실전: 전체 종목 2년치 수집 (주석 해제하여 사용)
    # collector.collect_all(
    #     timeframe='1',
    #     days_back=730,
    #     limit=None,
    #     delay=2.0
    # )


if __name__ == '__main__':
    main()
