"""
데이터 전처리 모듈
수집된 원본 분봉 데이터를 정제하고 필요한 시간대(09:00~10:15)만 추출합니다.
"""
import pandas as pd
from pathlib import Path
from datetime import time


class MinuteDataPreprocessor:
    """분봉 데이터 전처리"""
    
    def __init__(self, target_start=time(9, 0), target_end=time(10, 15)):
        """
        Args:
            target_start (time): 필터링 시작 시간 (기본 09:00)
            target_end (time): 필터링 종료 시간 (기본 10:15)
        """
        self.target_start = target_start
        self.target_end = target_end
    
    def load_minute_data(self, filepath):
        """
        CSV 파일에서 분봉 데이터 로드
        
        Args:
            filepath (str): CSV 파일 경로
            
        Returns:
            pd.DataFrame: 로드된 데이터
        """
        df = pd.read_csv(filepath, parse_dates=['timestamp'])
        return df
    
    def filter_target_timeframe(self, df):
        """
        목표 시간대(09:00~10:15)만 필터링
        
        Args:
            df (pd.DataFrame): 원본 데이터
            
        Returns:
            pd.DataFrame: 필터링된 데이터
        """
        df['time'] = df['timestamp'].dt.time
        filtered = df[(df['time'] >= self.target_start) & (df['time'] <= self.target_end)]
        return filtered.drop(columns=['time']).reset_index(drop=True)
    
    def add_technical_indicators(self, df):
        """
        기술적 지표 추가
        - 가격 변화율
        - 거래량 변화율
        - 이동평균
        
        Args:
            df (pd.DataFrame): 입력 데이터
            
        Returns:
            pd.DataFrame: 지표가 추가된 데이터
        """
        # 가격 변화율 (%)
        df['price_change'] = df['close'].pct_change() * 100
        
        # 거래량 변화율
        df['volume_change'] = df['volume'].pct_change() * 100
        
        # 3봉/5봉 이동평균
        df['ma3'] = df['close'].rolling(window=3).mean()
        df['ma5'] = df['close'].rolling(window=5).mean()
        
        # 거래량 이동평균
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        
        # 거래량 급증 비율 (현재 거래량 / 5봉 평균)
        df['volume_spike_ratio'] = df['volume'] / df['volume_ma5']
        
        return df
    
    def process_file(self, input_path, output_path):
        """
        단일 파일 전처리
        
        Args:
            input_path (str): 원본 파일 경로
            output_path (str): 저장 경로
        """
        # 로드
        df = self.load_minute_data(input_path)
        
        # 시간대 필터링
        df = self.filter_target_timeframe(df)
        
        # 지표 추가
        df = self.add_technical_indicators(df)
        
        # 저장
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        return df


def main():
    """테스트 실행"""
    preprocessor = MinuteDataPreprocessor()
    
    # 예시: 삼성전자 데이터 전처리
    input_file = '../../data/raw/005930_1min.csv'
    output_file = '../../data/processed/005930_1min_processed.csv'
    
    df = preprocessor.process_file(input_file, output_file)
    
    print(f"전처리 완료: {len(df)}개 레코드")
    print("\n=== 데이터 미리보기 ===")
    print(df.head(10))


if __name__ == '__main__':
    main()
