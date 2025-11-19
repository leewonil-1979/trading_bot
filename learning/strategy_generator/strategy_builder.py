"""
전략 생성 모듈
학습 결과를 기반으로 strategy.json을 자동 생성합니다.
"""
import json
import pandas as pd
from pathlib import Path


class StrategyGenerator:
    """전략 파일 생성기"""
    
    def __init__(self):
        self.strategy = {}
    
    def analyze_patterns(self, pattern_files):
        """
        여러 종목의 패턴 분석 결과를 통합 분석
        
        Args:
            pattern_files (list): 패턴 분석 파일 경로 리스트
            
        Returns:
            dict: 통합 통계
        """
        all_stats = []
        
        for filepath in pattern_files:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'statistics' in data:
                    all_stats.append(data['statistics'])
        
        if not all_stats:
            return {}
        
        # 평균 계산
        df = pd.DataFrame(all_stats)
        
        avg_stats = {
            'avg_win_rate': df['win_rate'].mean(),
            'avg_profit_rate': df['profit_rate'].mean(),
            'avg_return': df['avg_return'].mean(),
            'avg_breakout_rate': df['breakout_rate'].mean(),
            'avg_volume_spike': df['avg_volume_spike'].mean()
        }
        
        return avg_stats
    
    def generate_strategy(self, integrated_stats, backtest_results):
        """
        통합 분석 결과로부터 전략 생성
        
        Args:
            integrated_stats (dict): 통합 통계
            backtest_results (dict): 백테스트 결과
            
        Returns:
            dict: 생성된 전략
        """
        # 진입 조건 설정
        entry_conditions = {
            'vi_rebound': True,
            'min_rebound_rate': 0.02,  # 2% 이상 반등
            'volume_spike_ratio': max(2.0, integrated_stats.get('avg_volume_spike', 3.0)),
            'break_prev_high': integrated_stats.get('avg_breakout_rate', 0) > 30.0,
            'min_surge_rate': 0.05  # 상방 VI의 경우 5% 이상 급등
        }
        
        # 청산 조건 설정
        exit_conditions = {
            'take_profit': 0.03,       # +3%
            'stop_loss': -0.015,       # -1.5%
            'max_holding_minutes': 30,  # 30분 최대 보유
            'trailing_stop': 0.01      # 1% 트레일링 스탑
        }
        
        # 리스크 관리
        risk_management = {
            'max_position_size': 0.1,   # 자본의 10%
            'max_daily_trades': 5,       # 일일 최대 5회
            'max_daily_loss': -0.05,     # 일일 최대 손실 -5%
            'diversification': True      # 동시 여러 종목 분산
        }
        
        # 필터 조건
        filters = {
            'market_time_only': True,
            'target_timeframe': '09:00-10:15',
            'exclude_illiquid': True,
            'min_volume': 100000  # 최소 거래량
        }
        
        strategy = {
            'version': '1.0',
            'strategy_name': 'VI_Rebound_Pattern',
            'description': 'VI 발생 후 반등/돌파 패턴 기반 단타 전략',
            'entry': entry_conditions,
            'exit': exit_conditions,
            'risk_management': risk_management,
            'filters': filters,
            'expected_performance': {
                'win_rate': integrated_stats.get('avg_win_rate', 0),
                'avg_return': integrated_stats.get('avg_return', 0),
                'backtested_return': backtest_results.get('total_return', 0) if backtest_results else 0
            }
        }
        
        return strategy
    
    def save_strategy(self, strategy, output_path='../../config/strategy.json'):
        """
        전략을 JSON 파일로 저장
        
        Args:
            strategy (dict): 전략 딕셔너리
            output_path (str): 저장 경로
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, ensure_ascii=False, indent=2)
        
        print(f"\n=== 전략 생성 완료 ===")
        print(f"저장 경로: {output_path}")
        print(f"\n전략 요약:")
        print(f"  - 진입: VI 반등 {strategy['entry']['min_rebound_rate']*100}% 이상")
        print(f"  - 익절: {strategy['exit']['take_profit']*100}%")
        print(f"  - 손절: {strategy['exit']['stop_loss']*100}%")
        print(f"  - 예상 승률: {strategy['expected_performance']['win_rate']:.2f}%")


def main():
    """테스트 실행"""
    generator = StrategyGenerator()
    
    # 패턴 분석 파일 수집
    pattern_dir = Path('../../data/patterns')
    pattern_files = list(pattern_dir.glob('*_pattern_analysis.json'))
    
    # 통합 분석
    integrated_stats = generator.analyze_patterns(pattern_files)
    
    # 백테스트 결과 로드
    backtest_file = '../../data/patterns/backtest_results.json'
    backtest_results = {}
    if Path(backtest_file).exists():
        with open(backtest_file, 'r') as f:
            backtest_results = json.load(f)
    
    # 전략 생성
    strategy = generator.generate_strategy(integrated_stats, backtest_results)
    
    # 저장
    generator.save_strategy(strategy)


if __name__ == '__main__':
    main()
