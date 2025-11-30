"""
VI 반등 예측 모델
핵심: 프로그램 매수 유입 여부로 반등 확률 예측
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class VIReboundPredictor:
    """VI 이후 반등 예측기"""
    
    def __init__(self):
        self.rebound_patterns = []
        self.failure_patterns = []
    
    def analyze_vi_event(self, minute_data, investor_data, program_data, vi_time):
        """
        VI 발생 후 반등 가능성 분석
        
        Args:
            minute_data: 분봉 데이터
            investor_data: 투자자별 매매 데이터
            program_data: 프로그램 매매 데이터
            vi_time: VI 발생 시간
            
        Returns:
            dict: 반등 예측 결과
        """
        # VI 발생 후 5~15분 데이터 추출
        vi_idx = minute_data[minute_data['timestamp'] == vi_time].index[0]
        after_vi = minute_data.iloc[vi_idx:vi_idx+15]
        
        # ========== 1. 프로그램 매수 신호 (가장 중요!) ==========
        program_signal = self._check_program_buying(program_data, vi_time)
        
        # ========== 2. 기관/외국인 매수 신호 ==========
        institutional_signal = self._check_institutional_buying(investor_data, vi_time)
        
        # ========== 3. 거래량 패턴 ==========
        volume_signal = self._check_volume_pattern(after_vi)
        
        # ========== 4. 가격 패턴 ==========
        price_signal = self._check_price_pattern(after_vi)
        
        # ========== 5. 뉴스/공시 임팩트 ==========
        news_signal = 0  # 나중에 추가
        
        # ========== 종합 점수 계산 ==========
        rebound_score = (
            program_signal * 0.40 +        # 프로그램 매수 40% 가중치
            institutional_signal * 0.25 +  # 기관/외국인 25%
            volume_signal * 0.20 +         # 거래량 20%
            price_signal * 0.10 +          # 가격 패턴 10%
            news_signal * 0.05             # 뉴스 5%
        )
        
        return {
            'rebound_probability': rebound_score,
            'program_signal': program_signal,
            'institutional_signal': institutional_signal,
            'volume_signal': volume_signal,
            'price_signal': price_signal,
            'recommendation': self._make_recommendation(rebound_score)
        }
    
    def _check_program_buying(self, program_data, vi_time):
        """
        프로그램 매수 유입 체크 (핵심 신호!)
        
        Returns:
            float: 0~1 점수
        """
        # VI 후 5분간 프로그램 순매수량
        after_vi = program_data[program_data['time'] >= vi_time][:5]
        
        if len(after_vi) == 0:
            return 0.0
        
        net_program_buy = after_vi['program_buy'].sum() - after_vi['program_sell'].sum()
        avg_volume = program_data['program_buy'].mean()
        
        # 프로그램 순매수가 평균의 3배 이상 → 강한 매수 신호
        if net_program_buy > avg_volume * 3:
            return 1.0
        elif net_program_buy > avg_volume * 2:
            return 0.8
        elif net_program_buy > avg_volume:
            return 0.5
        elif net_program_buy > 0:
            return 0.3
        else:
            return 0.0
    
    def _check_institutional_buying(self, investor_data, vi_time):
        """
        기관/외국인 매수 체크
        
        Returns:
            float: 0~1 점수
        """
        after_vi = investor_data[investor_data['time'] >= vi_time][:5]
        
        if len(after_vi) == 0:
            return 0.0
        
        # 기관 순매수
        institutional_net = (
            after_vi['institutional_buy'].sum() - 
            after_vi['institutional_sell'].sum()
        )
        
        # 외국인 순매수
        foreign_net = (
            after_vi['foreign_buy'].sum() - 
            after_vi['foreign_sell'].sum()
        )
        
        # 둘 다 매수 → 1.0
        # 한쪽만 매수 → 0.5
        # 둘 다 매도 → 0.0
        if institutional_net > 0 and foreign_net > 0:
            return 1.0
        elif institutional_net > 0 or foreign_net > 0:
            return 0.5
        else:
            return 0.0
    
    def _check_volume_pattern(self, after_vi_df):
        """
        거래량 패턴 분석
        
        VI 해제 직후 거래량 폭발 → 반등 가능성 높음
        """
        if len(after_vi_df) < 3:
            return 0.0
        
        # VI 해제 후 첫 1분 거래량
        first_minute_vol = after_vi_df.iloc[0]['volume']
        avg_vol = after_vi_df['volume'].mean()
        
        if first_minute_vol > avg_vol * 5:
            return 1.0
        elif first_minute_vol > avg_vol * 3:
            return 0.7
        elif first_minute_vol > avg_vol * 2:
            return 0.4
        else:
            return 0.1
    
    def _check_price_pattern(self, after_vi_df):
        """
        가격 패턴 분석
        
        VI 후 즉시 반등 → 강세
        VI 후 횡보 → 중립
        VI 후 추가 하락 → 약세
        """
        if len(after_vi_df) < 5:
            return 0.0
        
        vi_price = after_vi_df.iloc[0]['close']
        price_5min = after_vi_df.iloc[4]['close']
        
        change = (price_5min - vi_price) / vi_price
        
        if change > 0.02:  # 2% 이상 반등
            return 1.0
        elif change > 0.01:  # 1% 반등
            return 0.7
        elif change > 0:  # 소폭 반등
            return 0.4
        elif change > -0.01:  # 횡보
            return 0.2
        else:  # 추가 하락
            return 0.0
    
    def _make_recommendation(self, score):
        """
        매매 추천
        
        Args:
            score: 반등 확률 점수 (0~1)
            
        Returns:
            str: BUY, HOLD, AVOID
        """
        if score >= 0.7:
            return "BUY"  # 강한 매수 신호
        elif score >= 0.5:
            return "HOLD"  # 관망
        else:
            return "AVOID"  # 회피
    
    def backtest_strategy(self, historical_data):
        """
        과거 데이터로 전략 백테스트
        
        Returns:
            dict: {
                'total_trades': 100,
                'win_rate': 0.75,
                'avg_profit': 0.025,
                'max_loss': -0.015
            }
        """
        trades = []
        
        for event in historical_data:
            prediction = self.analyze_vi_event(
                event['minute_data'],
                event['investor_data'],
                event['program_data'],
                event['vi_time']
            )
            
            # 실제 결과와 비교
            actual_result = event['actual_rebound']
            
            if prediction['recommendation'] == 'BUY':
                trades.append({
                    'predicted': prediction['rebound_probability'],
                    'actual': actual_result,
                    'profit': actual_result - 0.015  # 손절 -1.5%
                })
        
        # 승률 계산
        wins = [t for t in trades if t['profit'] > 0]
        win_rate = len(wins) / len(trades) if trades else 0
        
        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_profit': np.mean([t['profit'] for t in trades]),
            'max_loss': min([t['profit'] for t in trades]) if trades else 0
        }


def main():
    """사용 예제"""
    predictor = VIReboundPredictor()
    
    # 예제 데이터
    minute_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-15 09:00', periods=20, freq='1min'),
        'close': [50000, 49000, 48000, 47000, 46000,  # VI 발생
                  46500, 47000, 47500, 48000, 48500,  # 반등
                  49000, 49200, 49500, 49700, 50000,
                  50200, 50500, 50700, 51000, 51500],
        'volume': [10000, 30000, 50000, 80000, 100000,
                   150000, 80000, 50000, 40000, 30000,
                   25000, 20000, 18000, 15000, 12000,
                   10000, 9000, 8000, 7000, 6000]
    })
    
    program_data = pd.DataFrame({
        'time': pd.date_range('2024-01-15 09:00', periods=20, freq='1min'),
        'program_buy': [5000, 3000, 2000, 1000, 50000,  # VI 후 프로그램 매수 폭발!
                        40000, 30000, 20000, 15000, 10000,
                        8000, 6000, 5000, 4000, 3000,
                        2000, 1500, 1000, 800, 500],
        'program_sell': [5000] * 20
    })
    
    investor_data = pd.DataFrame({
        'time': pd.date_range('2024-01-15 09:00', periods=20, freq='1min'),
        'institutional_buy': [2000, 1000, 500, 200, 20000,
                              15000, 10000, 8000, 5000, 3000,
                              2000, 1500, 1000, 800, 500,
                              400, 300, 200, 100, 50],
        'institutional_sell': [2000] * 20,
        'foreign_buy': [1000] * 20,
        'foreign_sell': [1000] * 20
    })
    
    # VI 발생 시점
    vi_time = pd.Timestamp('2024-01-15 09:04')
    
    # 예측
    result = predictor.analyze_vi_event(
        minute_data, investor_data, program_data, vi_time
    )
    
    print("=== VI 반등 예측 결과 ===")
    print(f"반등 확률: {result['rebound_probability']:.2%}")
    print(f"프로그램 매수 신호: {result['program_signal']:.2f}")
    print(f"기관/외국인 신호: {result['institutional_signal']:.2f}")
    print(f"거래량 신호: {result['volume_signal']:.2f}")
    print(f"가격 패턴 신호: {result['price_signal']:.2f}")
    print(f"추천: {result['recommendation']}")


if __name__ == '__main__':
    main()
