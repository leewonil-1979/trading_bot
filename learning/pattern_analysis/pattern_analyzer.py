"""
VI 해제 후 반등/돌파 패턴 분석 모듈
탐지된 VI 이벤트에 대해 수익률, 승률 등을 분석합니다.
"""
import pandas as pd
import numpy as np
import json


class PatternAnalyzer:
    """VI 패턴 분석기"""
    
    def __init__(self, stop_loss=-0.015, take_profit=0.03):
        """
        Args:
            stop_loss (float): 손절 기준 (-1.5%)
            take_profit (float): 익절 기준 (+3%)
        """
        self.stop_loss = stop_loss
        self.take_profit = take_profit
    
    def analyze_rebound_pattern(self, df, vi_event):
        """
        VI 해제 후 반등 패턴 분석
        
        Args:
            df (pd.DataFrame): 분봉 데이터
            vi_event (dict): VI 이벤트 정보
            
        Returns:
            dict: 분석 결과
        """
        vi_idx = vi_event['index']
        
        # VI 해제 시점 (다음 캔들)
        if vi_idx + 1 >= len(df):
            return None
        
        entry_price = df.loc[vi_idx + 1, 'close']
        
        # 이후 10분/30분 가격 추적
        future_10min = df.loc[vi_idx+1:vi_idx+10] if vi_idx+10 < len(df) else df.loc[vi_idx+1:]
        future_30min = df.loc[vi_idx+1:vi_idx+30] if vi_idx+30 < len(df) else df.loc[vi_idx+1:]
        
        if len(future_10min) == 0:
            return None
        
        # 최고가/최저가
        max_price_10 = future_10min['high'].max()
        min_price_10 = future_10min['low'].min()
        
        # 수익률
        max_profit_10 = (max_price_10 - entry_price) / entry_price
        max_loss_10 = (min_price_10 - entry_price) / entry_price
        
        # 손절/익절 도달 여부
        stop_hit = max_loss_10 <= self.stop_loss
        profit_hit = max_profit_10 >= self.take_profit
        
        # 30분 후 종가
        final_price = future_30min.iloc[-1]['close'] if len(future_30min) > 0 else entry_price
        final_return = (final_price - entry_price) / entry_price
        
        # 전고점 돌파 여부 (VI 발생 전 최고가 대비)
        prev_high = df.loc[:vi_idx, 'high'].max()
        breakout = future_10min['high'].max() > prev_high
        
        # 거래량 분석
        avg_volume_before = df.loc[vi_idx-5:vi_idx, 'volume'].mean() if vi_idx >= 5 else df.loc[:vi_idx, 'volume'].mean()
        avg_volume_after = future_10min['volume'].mean()
        volume_spike = avg_volume_after / avg_volume_before if avg_volume_before > 0 else 0
        
        return {
            'vi_event': vi_event,
            'entry_price': entry_price,
            'max_profit_10min': max_profit_10,
            'max_loss_10min': max_loss_10,
            'final_return_30min': final_return,
            'stop_hit': stop_hit,
            'profit_hit': profit_hit,
            'breakout': breakout,
            'volume_spike_ratio': volume_spike
        }
    
    def batch_analyze(self, df, vi_events):
        """
        여러 VI 이벤트 일괄 분석
        
        Args:
            df (pd.DataFrame): 분봉 데이터
            vi_events (list): VI 이벤트 리스트
            
        Returns:
            list: 분석 결과 리스트
        """
        results = []
        
        for event in vi_events:
            result = self.analyze_rebound_pattern(df, event)
            if result:
                results.append(result)
        
        return results
    
    def calculate_statistics(self, analysis_results):
        """
        통계 계산 (승률, 평균 수익률 등)
        
        Args:
            analysis_results (list): 분석 결과 리스트
            
        Returns:
            dict: 통계 정보
        """
        if not analysis_results:
            return {}
        
        df = pd.DataFrame(analysis_results)
        
        # 승률 (손절 안 당한 비율)
        win_rate = (1 - df['stop_hit'].sum() / len(df)) * 100
        
        # 익절 달성률
        profit_rate = (df['profit_hit'].sum() / len(df)) * 100
        
        # 평균 수익률
        avg_return = df['final_return_30min'].mean() * 100
        
        # 전고점 돌파율
        breakout_rate = (df['breakout'].sum() / len(df)) * 100
        
        # 평균 거래량 급증 비율
        avg_volume_spike = df['volume_spike_ratio'].mean()
        
        return {
            'total_count': len(df),
            'win_rate': win_rate,
            'profit_rate': profit_rate,
            'avg_return': avg_return,
            'breakout_rate': breakout_rate,
            'avg_volume_spike': avg_volume_spike,
            'max_return': df['final_return_30min'].max() * 100,
            'min_return': df['final_return_30min'].min() * 100
        }
    
    def save_analysis(self, analysis_results, stock_code, output_path='../../data/patterns'):
        """
        분석 결과 저장
        
        Args:
            analysis_results (list): 분석 결과
            stock_code (str): 종목코드
            output_path (str): 저장 경로
        """
        from pathlib import Path
        
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        # 통계 계산
        stats = self.calculate_statistics(analysis_results)
        
        # 저장 데이터
        save_data = {
            'stock_code': stock_code,
            'statistics': stats,
            'details': analysis_results
        }
        
        filename = f"{output_path}/{stock_code}_pattern_analysis.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"패턴 분석 저장: {filename}")
        print(f"통계: {stats}")


def main():
    """테스트 실행"""
    # 예시 데이터 로드
    df = pd.read_csv('../../data/processed/005930_1min_processed.csv', parse_dates=['timestamp'])
    
    # VI 이벤트 로드
    with open('../../data/vi_events/005930_vi_events.json', 'r', encoding='utf-8') as f:
        vi_events = json.load(f)
    
    # 분석
    analyzer = PatternAnalyzer()
    results = analyzer.batch_analyze(df, vi_events)
    
    # 저장
    analyzer.save_analysis(results, '005930')


if __name__ == '__main__':
    main()
