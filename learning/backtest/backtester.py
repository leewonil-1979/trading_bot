"""
백테스팅 모듈
학습된 패턴을 기반으로 과거 데이터에서 수익률을 검증합니다.
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path


class Backtester:
    """백테스트 엔진"""
    
    def __init__(self, initial_capital=10000000, position_size=0.1):
        """
        Args:
            initial_capital (int): 초기 자본 (1천만원)
            position_size (float): 포지션 크기 (자본의 10%)
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.trades = []
        
    def run_backtest(self, df, vi_events, entry_rules, exit_rules):
        """
        백테스트 실행
        
        Args:
            df (pd.DataFrame): 분봉 데이터
            vi_events (list): VI 이벤트
            entry_rules (dict): 진입 조건
            exit_rules (dict): 청산 조건
            
        Returns:
            dict: 백테스트 결과
        """
        capital = self.initial_capital
        
        for event in vi_events:
            # 진입 조건 확인
            if not self._check_entry_rules(event, entry_rules):
                continue
            
            vi_idx = event['index']
            entry_idx = vi_idx + 1
            
            if entry_idx >= len(df):
                continue
            
            entry_price = df.loc[entry_idx, 'close']
            entry_time = df.loc[entry_idx, 'timestamp']
            
            # 투자 금액
            position_value = capital * self.position_size
            shares = int(position_value / entry_price)
            
            if shares == 0:
                continue
            
            # 청산 시뮬레이션
            exit_result = self._simulate_exit(df, entry_idx, entry_price, exit_rules)
            
            if exit_result:
                profit = (exit_result['exit_price'] - entry_price) * shares
                capital += profit
                
                trade_record = {
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_result['exit_time'],
                    'exit_price': exit_result['exit_price'],
                    'shares': shares,
                    'profit': profit,
                    'return': (exit_result['exit_price'] - entry_price) / entry_price,
                    'exit_reason': exit_result['reason']
                }
                
                self.trades.append(trade_record)
        
        # 결과 계산
        total_return = (capital - self.initial_capital) / self.initial_capital
        win_trades = [t for t in self.trades if t['profit'] > 0]
        win_rate = len(win_trades) / len(self.trades) * 100 if self.trades else 0
        
        avg_profit = np.mean([t['profit'] for t in self.trades]) if self.trades else 0
        max_profit = max([t['profit'] for t in self.trades]) if self.trades else 0
        max_loss = min([t['profit'] for t in self.trades]) if self.trades else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_return': total_return * 100,
            'total_trades': len(self.trades),
            'win_trades': len(win_trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'trades': self.trades
        }
    
    def _check_entry_rules(self, event, rules):
        """진입 조건 확인"""
        # 예: 반등률 최소 기준
        if 'min_rebound_rate' in rules:
            if event.get('rebound_rate', 0) < rules['min_rebound_rate']:
                return False
        
        # 예: 상승률 기준
        if 'min_surge_rate' in rules:
            if event.get('surge_rate', 0) < rules['min_surge_rate']:
                return False
        
        return True
    
    def _simulate_exit(self, df, entry_idx, entry_price, exit_rules):
        """청산 시뮬레이션"""
        stop_loss = exit_rules.get('stop_loss', -0.015)
        take_profit = exit_rules.get('take_profit', 0.03)
        max_holding = exit_rules.get('max_holding_bars', 30)
        
        # 이후 캔들 추적
        for i in range(1, max_holding + 1):
            idx = entry_idx + i
            
            if idx >= len(df):
                break
            
            current_price = df.loc[idx, 'close']
            current_return = (current_price - entry_price) / entry_price
            
            # 손절 확인
            if current_return <= stop_loss:
                return {
                    'exit_time': df.loc[idx, 'timestamp'],
                    'exit_price': current_price,
                    'reason': 'stop_loss'
                }
            
            # 익절 확인
            if current_return >= take_profit:
                return {
                    'exit_time': df.loc[idx, 'timestamp'],
                    'exit_price': current_price,
                    'reason': 'take_profit'
                }
        
        # 최대 보유 시간 도달
        final_idx = min(entry_idx + max_holding, len(df) - 1)
        return {
            'exit_time': df.loc[final_idx, 'timestamp'],
            'exit_price': df.loc[final_idx, 'close'],
            'reason': 'max_holding'
        }
    
    def save_results(self, results, output_path='../../data/patterns/backtest_results.json'):
        """백테스트 결과 저장"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"백테스트 결과 저장: {output_path}")


def main():
    """테스트 실행"""
    # 데이터 로드
    df = pd.read_csv('../../data/processed/005930_1min_processed.csv', parse_dates=['timestamp'])
    
    with open('../../data/vi_events/005930_vi_events.json', 'r') as f:
        vi_events = json.load(f)
    
    # 백테스트 설정
    entry_rules = {
        'min_rebound_rate': 0.02  # 2% 이상 반등
    }
    
    exit_rules = {
        'stop_loss': -0.015,      # -1.5%
        'take_profit': 0.03,       # +3%
        'max_holding_bars': 30     # 30분 최대 보유
    }
    
    # 백테스트 실행
    backtester = Backtester()
    results = backtester.run_backtest(df, vi_events, entry_rules, exit_rules)
    
    # 결과 출력
    print("\n=== 백테스트 결과 ===")
    print(f"초기 자본: {results['initial_capital']:,}원")
    print(f"최종 자본: {results['final_capital']:,}원")
    print(f"총 수익률: {results['total_return']:.2f}%")
    print(f"총 거래 수: {results['total_trades']}회")
    print(f"승률: {results['win_rate']:.2f}%")
    print(f"평균 수익: {results['avg_profit']:,}원")
    
    # 저장
    backtester.save_results(results)


if __name__ == '__main__':
    main()
