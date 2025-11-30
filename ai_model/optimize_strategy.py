"""
매매 전략 최적화
1. 거래량 필터링 (100만주 이상)
2. 최적 익절/손절 비율 탐색 (Grid Search)
3. 예수금별 전략 비교 (100만/1000만/1억)
4. 불타기/물타기 전략 비교
5. 최적 매수가 계산
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
import json
from itertools import product
import sys
sys.path.insert(0, './data_collection')


class StrategyOptimizer:
    def __init__(self, data_path='./data/crash_rebound/all_stocks_3years.parquet'):
        """전략 최적화 클래스"""
        self.df = pd.read_parquet(data_path)
        self.model = lgb.Booster(model_file='./models/crash_rebound_model.txt')
        self.feature_cols = [
            'crash_rate', 'close', 'volume', 'change_pct',
            'ma5', 'ma20', 'ma60', 'volume_ma20', 'volume_spike',
            'rsi', 'macd', 'macd_signal', 'macd_diff',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'stoch_k', 'stoch_d', 'atr',
            'institution_net', 'foreign_net', 'individual_net', 'program_net'
        ]
        
        # 급락 이벤트만 + AI 확률 계산
        self.df_crash = self.df[self.df['crash'] == 1].copy()
        X = self.df_crash[self.feature_cols].fillna(0)
        self.df_crash['ai_probability'] = self.model.predict(X)
        
    
    def filter_by_volume(self, min_volume=1_000_000):
        """거래량 필터링"""
        print(f"\n{'='*80}")
        print(f"1️⃣ 거래량 필터링 (최소 {min_volume:,}주)")
        print(f"{'='*80}\n")
        
        before = len(self.df_crash)
        self.df_crash = self.df_crash[self.df_crash['volume'] >= min_volume].copy()
        after = len(self.df_crash)
        
        print(f"필터링 전: {before}개 급락")
        print(f"필터링 후: {after}개 급락")
        print(f"제외: {before - after}개 ({(before - after) / before * 100:.1f}%)")
        print(f"\n💡 거래량 부족으로 체결 불가능한 종목 제외됨\n")
        
        return self.df_crash
    
    
    def find_optimal_take_profit_stop_loss(self, ai_threshold=0.6):
        """최적 익절/손절 비율 탐색 (Grid Search)"""
        print(f"\n{'='*80}")
        print(f"2️⃣ 최적 익절/손절 비율 탐색 (수익 극대화)")
        print(f"{'='*80}\n")
        
        # 고확률 종목만
        df_high = self.df_crash[self.df_crash['ai_probability'] >= ai_threshold].copy()
        
        print(f"분석 대상: {len(df_high)}개 급락 (AI 확률 {ai_threshold:.0%} 이상)\n")
        
        # Grid Search 범위
        take_profit_range = [0.05, 0.07, 0.10, 0.12, 0.15, 0.20]  # 5% ~ 20%
        stop_loss_range = [0.01, 0.02, 0.03, 0.05]  # -1% ~ -5%
        
        results = []
        
        print("탐색 중...\n")
        
        for tp, sl in product(take_profit_range, stop_loss_range):
            # 백테스트
            trades = []
            
            for idx, row in df_high.iterrows():
                # 5일간 일별 수익률
                daily_returns = []
                for day in range(1, 6):
                    col = f'rebound_d{day}'
                    if col in row.index:
                        daily_returns.append(row[col])
                
                if not daily_returns:
                    continue
                
                # 매수가 기준
                entry_price = 100  # 정규화
                max_reached = 0
                min_reached = 0
                exit_day = None
                exit_return = 0
                
                cumulative_return = 0
                for day, daily_ret in enumerate(daily_returns, 1):
                    cumulative_return += daily_ret
                    
                    # 익절 도달?
                    if cumulative_return >= tp:
                        exit_day = day
                        exit_return = tp
                        break
                    
                    # 손절 도달?
                    if cumulative_return <= -sl:
                        exit_day = day
                        exit_return = -sl
                        break
                
                # 5일 동안 익절/손절 안 되면 마지막 날 수익률
                if exit_day is None:
                    exit_day = len(daily_returns)
                    exit_return = cumulative_return
                
                trades.append({
                    'tp': tp,
                    'sl': sl,
                    'return': exit_return,
                    'days': exit_day,
                    'success': exit_return > 0
                })
            
            if not trades:
                continue
            
            # 통계
            total_trades = len(trades)
            success = sum(1 for t in trades if t['success'])
            win_rate = success / total_trades
            avg_return = np.mean([t['return'] for t in trades])
            total_return = sum([t['return'] for t in trades])
            avg_days = np.mean([t['days'] for t in trades])
            
            results.append({
                'take_profit': tp * 100,
                'stop_loss': sl * 100,
                'trades': total_trades,
                'win_rate': win_rate * 100,
                'avg_return': avg_return * 100,
                'total_return': total_return * 100,
                'avg_days': avg_days
            })
        
        # 결과 DataFrame
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('total_return', ascending=False)
        
        # 상위 10개 출력
        print("📊 최적 익절/손절 조합 (수익률 기준 Top 10):\n")
        print(f"{'순위':<5} {'익절':<8} {'손절':<8} {'거래':<6} {'승률':<10} {'평균수익':<12} {'총수익':<12} {'평균보유일':<10}")
        print("-" * 90)
        
        for i, row in df_results.head(10).iterrows():
            rank = int(df_results.index.get_loc(i)) + 1  # type: ignore
            print(f"{rank:<5} "
                  f"+{row['take_profit']:.0f}%{'':<4} "
                  f"-{row['stop_loss']:.0f}%{'':<4} "
                  f"{row['trades']:<6.0f} "
                  f"{row['win_rate']:<9.1f}% "
                  f"{row['avg_return']:<11.2f}% "
                  f"{row['total_return']:<11.1f}% "
                  f"{row['avg_days']:<9.1f}일")
        
        # 최적값
        best = df_results.iloc[0]
        
        print(f"\n{'='*90}")
        print(f"✅ 최적 조합:")
        print(f"   익절: +{best['take_profit']:.0f}%")
        print(f"   손절: -{best['stop_loss']:.0f}%")
        print(f"   승률: {best['win_rate']:.1f}%")
        print(f"   평균 수익: {best['avg_return']:.2f}%")
        print(f"   총 수익률: {best['total_return']:.1f}%")
        print(f"   평균 보유일: {best['avg_days']:.1f}일")
        print(f"{'='*90}\n")
        
        return df_results, best
    
    
    def compare_capital_strategies(self, best_tp, best_sl, ai_threshold=0.6):
        """예수금별 전략 비교"""
        print(f"\n{'='*80}")
        print(f"3️⃣ 예수금별 전략 비교")
        print(f"{'='*80}\n")
        
        capitals = [1_000_000, 10_000_000, 100_000_000]  # 100만, 1000만, 1억
        
        df_high = self.df_crash[self.df_crash['ai_probability'] >= ai_threshold].copy()
        df_high = df_high.sort_values('ai_probability', ascending=False)
        
        print(f"분석 대상: {len(df_high)}개 급락 (AI 확률 {ai_threshold:.0%}+)\n")
        print(f"익절: +{best_tp:.0f}%, 손절: -{best_sl:.0f}%\n")
        
        results = []
        
        for capital in capitals:
            # 1회 투자금 = 예수금의 10%
            position_size = capital * 0.1
            
            # 백테스트
            total_profit = 0
            trades = 0
            wins = 0
            
            for idx, row in df_high.iterrows():
                # 거래량 체크 (체결 가능 여부)
                if row['volume'] < position_size / row['close']:
                    continue  # 거래량 부족, 매수 불가
                
                # 수익률 계산
                daily_returns = []
                for day in range(1, 6):
                    col = f'rebound_d{day}'
                    if col in row.index:
                        daily_returns.append(row[col])
                
                if not daily_returns:
                    continue
                
                cumulative_return = 0
                for daily_ret in daily_returns:
                    cumulative_return += daily_ret
                    
                    # 익절
                    if cumulative_return >= best_tp / 100:
                        profit = position_size * (best_tp / 100)
                        total_profit += profit
                        wins += 1
                        trades += 1
                        break
                    
                    # 손절
                    if cumulative_return <= -(best_sl / 100):
                        profit = position_size * (-(best_sl / 100))
                        total_profit += profit
                        trades += 1
                        break
                else:
                    # 5일 종료
                    profit = position_size * cumulative_return
                    total_profit += profit
                    if cumulative_return > 0:
                        wins += 1
                    trades += 1
            
            win_rate = wins / trades * 100 if trades > 0 else 0
            return_rate = total_profit / capital * 100
            
            results.append({
                'capital': capital,
                'position_size': position_size,
                'trades': trades,
                'wins': wins,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'return_rate': return_rate
            })
        
        # 결과 출력
        print(f"{'예수금':<15} {'1회투자':<15} {'거래수':<10} {'승률':<12} {'총수익':<15} {'수익률':<10}")
        print("-" * 90)
        
        for r in results:
            print(f"{r['capital']:>13,}원 "
                  f"{r['position_size']:>13,.0f}원 "
                  f"{r['trades']:>8}회 "
                  f"{r['win_rate']:>10.1f}% "
                  f"{r['total_profit']:>13,.0f}원 "
                  f"{r['return_rate']:>8.1f}%")
        
        print()
        return results
    
    
    def compare_averaging_strategies(self, capital, best_tp, best_sl, ai_threshold=0.6):
        """불타기/물타기 전략 비교"""
        print(f"\n{'='*80}")
        print(f"4️⃣ 불타기/물타기 전략 비교 (예수금: {capital:,}원)")
        print(f"{'='*80}\n")
        
        df_high = self.df_crash[self.df_crash['ai_probability'] >= ai_threshold].copy()
        df_high = df_high.sort_values('ai_probability', ascending=False)
        
        strategies = []
        
        # ========================================
        # 전략 1: 예수금 100% 1회 매수
        # ========================================
        print("전략 1: 예수금 100% 1회 매수 (불타기/물타기 없음)")
        print("-" * 80)
        
        position_size = capital
        total_profit_s1 = 0
        trades_s1 = 0
        wins_s1 = 0
        
        for idx, row in df_high.iterrows():
            # 거래량 체크
            if row['volume'] < position_size / row['close']:
                continue
            
            daily_returns = []
            for day in range(1, 6):
                col = f'rebound_d{day}'
                if col in row.index:
                    daily_returns.append(row[col])
            
            if not daily_returns:
                continue
            
            cumulative_return = 0
            for daily_ret in daily_returns:
                cumulative_return += daily_ret
                
                if cumulative_return >= best_tp / 100:
                    profit = position_size * (best_tp / 100)
                    total_profit_s1 += profit
                    wins_s1 += 1
                    trades_s1 += 1
                    break
                
                if cumulative_return <= -(best_sl / 100):
                    profit = position_size * (-(best_sl / 100))
                    total_profit_s1 += profit
                    trades_s1 += 1
                    break
            else:
                profit = position_size * cumulative_return
                total_profit_s1 += profit
                if cumulative_return > 0:
                    wins_s1 += 1
                trades_s1 += 1
        
        win_rate_s1 = wins_s1 / trades_s1 * 100 if trades_s1 > 0 else 0
        return_rate_s1 = total_profit_s1 / capital * 100
        
        print(f"거래: {trades_s1}회")
        print(f"승률: {win_rate_s1:.1f}%")
        print(f"총 수익: {total_profit_s1:,.0f}원")
        print(f"수익률: {return_rate_s1:.1f}%")
        print()
        
        strategies.append({
            'name': '100% 1회 매수',
            'trades': trades_s1,
            'wins': wins_s1,
            'win_rate': win_rate_s1,
            'total_profit': total_profit_s1,
            'return_rate': return_rate_s1
        })
        
        # ========================================
        # 전략 2: 예수금 50% + 물타기 1회
        # ========================================
        print("전략 2: 예수금 50% + 물타기 1회 (하락 시)")
        print("-" * 80)
        
        position_size_initial = capital * 0.5
        position_size_avg = capital * 0.5
        
        total_profit_s2 = 0
        trades_s2 = 0
        wins_s2 = 0
        avg_used = 0  # 물타기 사용 횟수
        
        for idx, row in df_high.iterrows():
            # 거래량 체크 (최대 투자 = 100%)
            if row['volume'] < capital / row['close']:
                continue
            
            daily_returns = []
            for day in range(1, 6):
                col = f'rebound_d{day}'
                if col in row.index:
                    daily_returns.append(row[col])
            
            if not daily_returns:
                continue
            
            # 1차 매수
            invested = position_size_initial
            avg_used_this_trade = False
            
            cumulative_return = 0
            for daily_ret in daily_returns:
                cumulative_return += daily_ret
                
                # 물타기 조건: -1% 하락 시 (아직 물타기 안 함)
                if cumulative_return <= -0.01 and not avg_used_this_trade:
                    # 추가 매수 (평균 단가 계산)
                    invested += position_size_avg
                    avg_used_this_trade = True
                    avg_used += 1
                    # 평균 단가 효과로 손익 재계산
                    # 간단화: 50% + 50% = 평균 -0.5% 시점에서 추가 매수
                    cumulative_return = cumulative_return * 0.5  # 평균 단가 효과
                
                # 익절 (투자금 기준)
                if cumulative_return >= best_tp / 100:
                    profit = invested * (best_tp / 100)
                    total_profit_s2 += profit
                    wins_s2 += 1
                    trades_s2 += 1
                    break
                
                # 손절
                if cumulative_return <= -(best_sl / 100):
                    profit = invested * (-(best_sl / 100))
                    total_profit_s2 += profit
                    trades_s2 += 1
                    break
            else:
                profit = invested * cumulative_return
                total_profit_s2 += profit
                if cumulative_return > 0:
                    wins_s2 += 1
                trades_s2 += 1
        
        win_rate_s2 = wins_s2 / trades_s2 * 100 if trades_s2 > 0 else 0
        return_rate_s2 = total_profit_s2 / capital * 100
        
        print(f"거래: {trades_s2}회")
        print(f"물타기 사용: {avg_used}회 ({avg_used/trades_s2*100:.1f}%)")
        print(f"승률: {win_rate_s2:.1f}%")
        print(f"총 수익: {total_profit_s2:,.0f}원")
        print(f"수익률: {return_rate_s2:.1f}%")
        print()
        
        strategies.append({
            'name': '50% + 물타기 1회',
            'trades': trades_s2,
            'wins': wins_s2,
            'win_rate': win_rate_s2,
            'total_profit': total_profit_s2,
            'return_rate': return_rate_s2,
            'avg_used': avg_used
        })
        
        # 비교
        print("=" * 80)
        print("📊 전략 비교:")
        print("-" * 80)
        print(f"{'전략':<20} {'거래':<10} {'승률':<12} {'총수익':<20} {'수익률':<10}")
        print("-" * 80)
        for s in strategies:
            print(f"{s['name']:<20} {s['trades']:>8}회 {s['win_rate']:>10.1f}% {s['total_profit']:>18,.0f}원 {s['return_rate']:>8.1f}%")
        
        print("=" * 80)
        
        if return_rate_s1 > return_rate_s2:
            print("✅ 결론: 예수금 100% 1회 매수가 더 유리!")
            print(f"   차이: +{return_rate_s1 - return_rate_s2:.1f}%p")
        else:
            print("✅ 결론: 예수금 50% + 물타기 1회가 더 유리!")
            print(f"   차이: +{return_rate_s2 - return_rate_s1:.1f}%p")
        
        print("=" * 80)
        print()
        
        return strategies
    
    
    def calculate_optimal_entry_price(self, ai_threshold=0.6):
        """최적 매수가 계산 (시초가 대비)"""
        print(f"\n{'='*80}")
        print(f"5️⃣ 최적 매수가 계산 (지정가)")
        print(f"{'='*80}\n")
        
        df_high = self.df_crash[self.df_crash['ai_probability'] >= ai_threshold].copy()
        
        print(f"분석 대상: {len(df_high)}개 급락\n")
        
        # 급락 다음날 시초가 vs 종가 대비 분석
        # (간단화: 다음날 open이 있다고 가정)
        # 실제로는 다음날 데이터가 필요하지만, 여기서는 rebound_d1 사용
        
        print("💡 매수 전략:")
        print("-" * 80)
        print()
        
        print("전략 A: 시장가 매수 (09:00 시초가)")
        print("   장점: 확실한 체결")
        print("   단점: 갭 상승 시 높은 가격에 매수")
        print()
        
        print("전략 B: 지정가 매수 (전일 종가 기준)")
        print("   장점: 유리한 가격 진입")
        print("   단점: 체결 안 될 수 있음")
        print()
        
        print("📊 시초가 갭 분석:")
        print("-" * 80)
        
        # 실제 데이터에는 다음날 시초가 정보 없음
        # 대신 rebound_d1로 추정
        
        df_high['next_day_return'] = df_high['rebound_d1']
        
        # 시초가 갭 추정 (당일 종가 대비 다음날 변화)
        gap_up = len(df_high[df_high['next_day_return'] > 0.02])  # +2% 이상 갭 상승
        gap_flat = len(df_high[(df_high['next_day_return'] >= -0.02) & (df_high['next_day_return'] <= 0.02)])
        gap_down = len(df_high[df_high['next_day_return'] < -0.02])  # -2% 이상 갭 하락
        
        total = len(df_high)
        
        print(f"갭 상승 (+2% 이상): {gap_up}회 ({gap_up/total*100:.1f}%)")
        print(f"보합 (±2% 이내): {gap_flat}회 ({gap_flat/total*100:.1f}%)")
        print(f"갭 하락 (-2% 이상): {gap_down}회 ({gap_down/total*100:.1f}%)")
        print()
        
        print("✅ 권장 전략:")
        print("-" * 80)
        print()
        
        if gap_up / total > 0.5:
            print("📈 갭 상승 비율이 높음 (50% 이상)")
            print("   → 시장가 매수 권장")
            print("   → 갭 상승해도 반등하면 수익")
        elif gap_down / total > 0.3:
            print("📉 갭 하락 비율이 높음 (30% 이상)")
            print("   → 지정가 매수 권장 (전일 종가 -1%)")
            print("   → 유리한 가격 진입")
        else:
            print("📊 혼합 전략 권장")
            print("   → 50%: 시장가 매수 (확실한 체결)")
            print("   → 50%: 지정가 매수 (전일 종가 기준, 유리한 가격)")
        
        print()
        print("💰 지정가 설정 가이드:")
        print("-" * 80)
        print("   전일 종가: 10,000원")
        print("   지정가 1: 10,000원 (전일 종가)")
        print("   지정가 2: 9,900원 (전일 종가 -1%)")
        print("   지정가 3: 9,800원 (전일 종가 -2%)")
        print()
        print("   → 체결률과 진입가 trade-off 고려")
        print()
        
        return gap_up, gap_flat, gap_down


def main():
    """최적화 실행"""
    
    print("\n" + "="*80)
    print("🔬 급락 후 반등 매매 전략 최적화")
    print("="*80)
    
    optimizer = StrategyOptimizer()
    
    # 1. 거래량 필터링
    optimizer.filter_by_volume(min_volume=1_000_000)
    
    # 2. 최적 익절/손절 탐색
    df_results, best = optimizer.find_optimal_take_profit_stop_loss(ai_threshold=0.6)
    
    # 3. 예수금별 전략
    optimizer.compare_capital_strategies(
        best_tp=best['take_profit'],
        best_sl=best['stop_loss'],
        ai_threshold=0.6
    )
    
    # 4. 불타기/물타기 비교 (1000만원 기준)
    optimizer.compare_averaging_strategies(
        capital=10_000_000,
        best_tp=best['take_profit'],
        best_sl=best['stop_loss'],
        ai_threshold=0.6
    )
    
    # 5. 최적 매수가
    optimizer.calculate_optimal_entry_price(ai_threshold=0.6)
    
    # 결과 저장
    df_results.to_csv('./models/optimal_strategy.csv', index=False)
    
    with open('./models/optimal_params.json', 'w') as f:
        json.dump({
            'take_profit': best['take_profit'],
            'stop_loss': best['stop_loss'],
            'win_rate': best['win_rate'],
            'avg_return': best['avg_return'],
            'total_return': best['total_return'],
            'avg_days': best['avg_days']
        }, f, indent=2)
    
    print("\n" + "="*80)
    print("✅ 최적화 완료!")
    print("="*80)
    print()
    print("저장된 파일:")
    print("   - models/optimal_strategy.csv (전체 결과)")
    print("   - models/optimal_params.json (최적 파라미터)")
    print()


if __name__ == '__main__':
    main()
