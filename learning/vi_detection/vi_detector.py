"""
VI (변동성완화장치) 구간 자동 탐지 모듈
분봉 데이터에서 VI 발생 구간을 역추적합니다.
"""
import pandas as pd
import numpy as np
from datetime import time


class VIDetector:
    """VI 구간 탐지기"""
    
    def __init__(self, gap_threshold=0.07, freeze_threshold=0.08):
        """
        Args:
            gap_threshold (float): 갭 하락/상승 기준 (7%)
            freeze_threshold (float): VI 발동 기준 (8%)
        """
        self.gap_threshold = gap_threshold
        self.freeze_threshold = freeze_threshold
    
    def detect_gap_down_vi(self, df, market_open_time=time(9, 0)):
        """
        9시 정각 하방 VI 패턴 탐지
        
        조건:
        1. 시초가 갭 하락 -7% ~ -10%
        2. 9:00~9:01 구간 거래량/가격 이상 패턴
        3. VI 해제 후 급등 패턴
        
        Args:
            df (pd.DataFrame): 분봉 데이터
            market_open_time (time): 장 시작 시간
            
        Returns:
            list: VI 이벤트 리스트 [{'index': idx, 'type': 'down_vi', ...}]
        """
        df['time'] = pd.to_datetime(df['timestamp']).dt.time
        
        vi_events = []
        
        # 9시 정각 데이터만 추출
        open_candles = df[df['time'] == market_open_time].copy()
        
        for idx, row in open_candles.iterrows():
            # 전일 종가 대비 갭 계산 (실제로는 전일 종가 데이터 필요)
            # 임시: 첫 캔들의 시가-저가 비율로 갭 추정
            
            open_price = row['open']
            low_price = row['low']
            
            # 갭 하락률 추정
            gap_rate = (low_price - open_price) / open_price
            
            if gap_rate < -self.gap_threshold:
                # 하방 VI 의심 구간
                
                # 다음 몇 개 캔들 확인 (VI 해제 후 반등 패턴)
                next_candles = df[df.index > idx].head(10)
                
                if len(next_candles) > 0:
                    # 반등 여부 확인
                    rebound_rate = (next_candles['high'].max() - row['low']) / row['low']
                    
                    if rebound_rate > 0.01:  # 1% 이상 반등
                        vi_events.append({
                            'index': idx,
                            'type': 'down_vi',
                            'timestamp': row['timestamp'],
                            'gap_rate': gap_rate,
                            'open': open_price,
                            'low': low_price,
                            'rebound_rate': rebound_rate
                        })
        
        return vi_events
    
    def detect_upward_vi(self, df):
        """
        상방 VI 패턴 탐지 (급등 후 정지)
        
        조건:
        1. 단기 급등 5~10%
        2. 거래 중지 패턴 (거래량 급감 또는 가격 동결)
        3. 재상승 패턴
        
        Args:
            df (pd.DataFrame): 분봉 데이터
            
        Returns:
            list: VI 이벤트 리스트
        """
        vi_events = []
        
        # 5봉 상승률 계산
        df['price_5_change'] = df['close'].pct_change(5) * 100
        
        # 급등 구간 탐지
        surge_indices = df[df['price_5_change'] > 5.0].index
        
        for idx in surge_indices:
            if idx + 5 >= len(df):
                continue
            
            # 급등 후 5개 캔들 확인
            next_candles = df.loc[idx+1:idx+5]
            
            # 거래량 급감 여부 (VI 정지 패턴)
            volume_drop = next_candles['volume'].mean() < df.loc[idx, 'volume'] * 0.3
            
            # 가격 횡보 여부
            price_range = (next_candles['high'].max() - next_candles['low'].min()) / df.loc[idx, 'close']
            
            if volume_drop and price_range < 0.02:  # 2% 미만 변동
                # 상방 VI 의심
                
                # 이후 재상승 확인
                later_candles = df.loc[idx+6:idx+15] if idx+15 < len(df) else df.loc[idx+6:]
                
                if len(later_candles) > 0:
                    breakout = (later_candles['close'].max() - df.loc[idx, 'close']) / df.loc[idx, 'close']
                    
                    if breakout > 0.02:  # 2% 이상 재상승
                        vi_events.append({
                            'index': idx,
                            'type': 'up_vi',
                            'timestamp': df.loc[idx, 'timestamp'],
                            'surge_rate': df.loc[idx, 'price_5_change'],
                            'breakout_rate': breakout
                        })
        
        return vi_events
    
    def save_vi_events(self, vi_events, stock_code, output_path='../../data/vi_events'):
        """
        탐지된 VI 이벤트 저장
        
        Args:
            vi_events (list): VI 이벤트 리스트
            stock_code (str): 종목코드
            output_path (str): 저장 디렉토리
        """
        import json
        from pathlib import Path
        
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        filename = f"{output_path}/{stock_code}_vi_events.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(vi_events, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"VI 이벤트 저장: {filename} ({len(vi_events)}개)")


def main():
    """테스트 실행"""
    detector = VIDetector()
    
    # 예시 데이터 로드
    df = pd.read_csv('../../data/processed/005930_1min_processed.csv', parse_dates=['timestamp'])
    
    # 하방 VI 탐지
    down_vi = detector.detect_gap_down_vi(df)
    print(f"하방 VI 탐지: {len(down_vi)}개")
    
    # 상방 VI 탐지
    up_vi = detector.detect_upward_vi(df)
    print(f"상방 VI 탐지: {len(up_vi)}개")
    
    # 저장
    all_events = down_vi + up_vi
    detector.save_vi_events(all_events, '005930')


if __name__ == '__main__':
    main()
