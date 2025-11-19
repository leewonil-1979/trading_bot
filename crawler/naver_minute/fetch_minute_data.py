"""
네이버 금융 분봉 데이터 수집 모듈
1분봉/3분봉 과거 데이터를 크롤링합니다.
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json
from pathlib import Path


class NaverMinuteFetcher:
    """네이버 금융 분봉 데이터 크롤러"""
    
    def __init__(self):
        # 네이버 금융 차트 API 엔드포인트
        self.base_url = "https://api.finance.naver.com/siseJson.naver"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.naver.com/'
        }
        
    def fetch_minute_data(self, stock_code, timeframe='1', count=900):
        """
        특정 종목의 분봉 데이터 수집
        
        Args:
            stock_code (str): 종목코드 (6자리)
            timeframe (str): '1' (1분봉) 또는 '3' (3분봉)
            count (int): 수집할 캔들 개수 (최대 900)
            
        Returns:
            pd.DataFrame: 분봉 데이터 (시간, OHLCV)
        """
        params = {
            'symbol': stock_code,
            'requestType': timeframe,  # 1: 1분, 3: 3분, 5: 5분
            'startTime': '',
            'endTime': '',
            'timeframe': 'day',
            'count': count
        }
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"[{stock_code}] API 요청 실패: {response.status_code}")
                return None
            
            # 응답 데이터 파싱 (JSON 형태)
            data = response.json()
            
            if not data or len(data) < 2:
                print(f"[{stock_code}] 데이터 없음")
                return None
            
            # 첫 줄은 헤더
            columns = data[0]
            rows = data[1:]
            
            # DataFrame 생성
            df = pd.DataFrame(rows, columns=columns)
            
            # 컬럼명 정리
            df = df.rename(columns={
                '체결시간': 'timestamp',
                '시가': 'open',
                '고가': 'high',
                '저가': 'low',
                '종가': 'close',
                '거래량': 'volume'
            })
            
            # 데이터 타입 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y%m%d%H%M%S')
            df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
            df['volume'] = df['volume'].astype(int)
            
            # 시간순 정렬
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"[{stock_code}] 데이터 수집 오류: {e}")
            return None
    
    def fetch_historical_data(self, stock_code, stock_name='', timeframe='1', days_back=730):
        """
        특정 종목의 과거 분봉 데이터 수집 (최대 2년치)
        
        Args:
            stock_code (str): 종목코드
            stock_name (str): 종목명 (로그용)
            timeframe (str): '1' 또는 '3'
            days_back (int): 수집할 과거 일수 (기본 730일 = 2년)
            
        Returns:
            pd.DataFrame: 분봉 데이터
        """
        print(f"[{stock_code} {stock_name}] {timeframe}분봉 데이터 수집 중...")
        
        all_data = []
        
        # 네이버는 최대 900개씩만 제공 → 여러 번 요청 필요
        # 1분봉 기준: 하루 약 375개 (09:00~15:30)
        # 900개 ≈ 2.4일치
        
        max_iterations = (days_back // 2) + 1  # 안전하게 여유있게
        
        for i in range(max_iterations):
            df = self.fetch_minute_data(stock_code, timeframe, count=900)
            
            if df is None or df.empty:
                break
            
            all_data.append(df)
            
            # 가장 오래된 날짜 확인
            oldest_date = df['timestamp'].min()
            target_date = datetime.now() - timedelta(days=days_back)
            
            if oldest_date < target_date:
                print(f"  목표 기간 도달: {oldest_date.date()}")
                break
            
            print(f"  {i+1}차 수집: {len(df)}개, 최근 날짜: {oldest_date.date()}")
            time.sleep(0.5)  # API 부하 방지
        
        if not all_data:
            print(f"[{stock_code}] 수집된 데이터 없음")
            return None
        
        # 전체 데이터 병합
        result = pd.concat(all_data, ignore_index=True)
        result = result.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        # 지정 기간만 필터링
        cutoff_date = datetime.now() - timedelta(days=days_back)
        result = result[result['timestamp'] >= cutoff_date]
        
        print(f"[{stock_code}] 총 {len(result)}개 분봉 수집 완료 ({result['timestamp'].min().date()} ~ {result['timestamp'].max().date()})\n")
        
        return result
    
    def save_to_csv(self, df, stock_code, timeframe='1', output_dir='../../data/raw'):
        """
        분봉 데이터를 CSV로 저장
        
        Args:
            df (pd.DataFrame): 저장할 데이터
            stock_code (str): 종목코드
            timeframe (str): 분봉 단위
            output_dir (str): 저장 디렉토리
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = f"{stock_code}_{timeframe}min.csv"
        filepath = f"{output_dir}/{filename}"
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"저장 완료: {filepath}")


def main():
    """테스트 실행"""
    fetcher = NaverMinuteFetcher()
    
    # 삼성전자 1분봉 테스트
    test_code = '005930'
    df = fetcher.fetch_historical_data(test_code, '삼성전자', timeframe='1', days_back=30)
    
    if df is not None:
        fetcher.save_to_csv(df, test_code, timeframe='1')
        print("\n=== 데이터 미리보기 ===")
        print(df.head())
        print(df.tail())


if __name__ == '__main__':
    main()
