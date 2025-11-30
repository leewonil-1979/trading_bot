"""
급락 후 반등 예측 AI 모델 학습

모델: LightGBM (Gradient Boosting)
목표: 급락 후 5일 내 +10% 이상 반등 예측
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import joblib


class CrashReboundModel:
    """급락 후 반등 예측 모델"""
    
    def __init__(self, data_path='./data/crash_rebound/all_stocks_3years.parquet'):
        self.data_path = Path(data_path)
        self.model = None
        self.feature_importance = None
        
        print(f"\n{'='*60}")
        print(f"🤖 급락 후 반등 예측 AI 모델 학습")
        print(f"{'='*60}\n")
    
    # =========================================
    # 1. 데이터 로드 및 전처리
    # =========================================
    
    def load_data(self):
        """데이터 로드"""
        print("📂 데이터 로드 중...")
        
        df = pd.read_parquet(self.data_path)
        
        print(f"✅ 총 데이터: {len(df):,}행")
        print(f"   급락 이벤트: {df['crash'].sum():,}회")
        print(f"   성공 반등: {df['success'].sum():,}회")
        print(f"   성공률: {df['success'].sum() / df['crash'].sum() * 100:.1f}%\n")
        
        return df
    
    def prepare_features(self, df):
        """
        학습용 Feature 준비
        
        Returns:
            X: Feature DataFrame
            y: Label (success)
        """
        print("🔧 Feature 준비 중...")
        
        # 급락 이벤트만 필터링
        df_crash = df[df['crash'] == 1].copy()
        
        print(f"   급락 이벤트: {len(df_crash):,}개")
        
        # Feature 선택
        feature_cols = [
            # 급락 정보
            'crash_rate',
            
            # 주가 정보
            'close', 'volume', 'change_pct',
            
            # 이동평균
            'ma5', 'ma20', 'ma60',
            
            # 거래량
            'volume_ma20', 'volume_spike',
            
            # 기술적 지표
            'rsi', 'macd', 'macd_signal', 'macd_diff',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'stoch_k', 'stoch_d', 'atr',
            
            # 투자자별 매매 (일부 종목은 0)
            'institution_net', 'foreign_net', 'individual_net', 'program_net'
        ]
        
        # 결측치 제거
        df_crash = df_crash.dropna(subset=feature_cols + ['success'])
        
        X = df_crash[feature_cols]
        y = df_crash['success']
        
        print(f"   최종 데이터: {len(X):,}개")
        print(f"   성공 반등: {y.sum():,}개 ({y.sum() / len(y) * 100:.1f}%)")
        print(f"   Feature 수: {len(feature_cols)}개\n")
        
        return X, y, df_crash
    
    # =========================================
    # 2. 모델 학습
    # =========================================
    
    def train(self, X, y):
        """
        LightGBM 모델 학습
        """
        print("🎓 모델 학습 중...\n")
        
        # Train/Test 분할 (시계열 고려 - 최근 20%를 테스트)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        print(f"   학습 데이터: {len(X_train):,}개")
        print(f"   테스트 데이터: {len(X_test):,}개\n")
        
        # LightGBM 데이터셋
        train_data = lgb.Dataset(X_train, label=y_train)
        test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        # 하이퍼파라미터
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42
        }
        
        # 학습
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=500,
            valid_sets=[train_data, test_data],
            valid_names=['train', 'test'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50),
                lgb.log_evaluation(period=100)
            ]
        )
        
        print("\n✅ 학습 완료!\n")
        
        return X_train, X_test, y_train, y_test
    
    # =========================================
    # 3. 모델 평가
    # =========================================
    
    def evaluate(self, X_test, y_test):
        """모델 성능 평가"""
        print("📊 모델 평가 중...\n")
        
        if self.model is None:
            print("❌ 모델이 학습되지 않았습니다.")
            return None
        
        # 예측
        y_pred_proba = self.model.predict(X_test)  # type: ignore
        y_pred = (y_pred_proba > 0.5).astype(int)  # type: ignore
        
        # 평가 지표
        print("=" * 60)
        print("분류 성능")
        print("=" * 60)
        print(classification_report(y_test, y_pred, target_names=['실패', '성공']))
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        print("\nConfusion Matrix:")
        print(f"              예측 실패  예측 성공")
        print(f"실제 실패:     {cm[0][0]:>6}    {cm[0][1]:>6}")
        print(f"실제 성공:     {cm[1][0]:>6}    {cm[1][1]:>6}\n")
        
        # AUC
        auc = roc_auc_score(y_test, y_pred_proba)  # type: ignore
        print(f"AUC Score: {auc:.4f}\n")
        
        return y_pred_proba
    
    def analyze_feature_importance(self):
        """Feature 중요도 분석"""
        print("📈 Feature 중요도 분석...\n")
        
        if self.model is None:
            print("❌ 모델이 학습되지 않았습니다.")
            return
        
        importance = self.model.feature_importance(importance_type='gain')  # type: ignore
        feature_names = self.model.feature_name()  # type: ignore
        
        self.feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        print("Top 10 중요 Feature:")
        print(self.feature_importance.head(10).to_string(index=False))
        print()
    
    # =========================================
    # 4. 수익 시뮬레이션
    # =========================================
    
    def simulate_profit(self, df_crash, y_pred_proba, threshold=0.6):
        """
        실전 수익 시뮬레이션
        
        Args:
            threshold: 매수 확률 임계값 (0.6 = 60% 이상만 매수)
        """
        print(f"💰 수익 시뮬레이션 (확률 {threshold*100:.0f}% 이상만 매수)\n")
        
        # 테스트 데이터만 (최근 20%)
        split_idx = int(len(df_crash) * 0.8)
        df_test = df_crash.iloc[split_idx:].copy()
        df_test['pred_proba'] = y_pred_proba
        
        # 매수 대상 (확률 threshold 이상)
        df_trade = df_test[df_test['pred_proba'] >= threshold].copy()
        
        print(f"   테스트 급락: {len(df_test)}회")
        print(f"   매수 대상: {len(df_trade)}회 ({len(df_trade)/len(df_test)*100:.1f}%)\n")
        
        if len(df_trade) == 0:
            print("⚠️ 매수 대상 없음 (임계값 너무 높음)")
            return
        
        # 수익 계산
        total_profit = 0
        win_count = 0
        lose_count = 0
        
        for idx, row in df_trade.iterrows():
            # 5일 내 최대 반등률
            profit = row['rebound_d5']
            
            if profit >= 0.10:  # +10% 이상
                win_count += 1
                total_profit += 0.10  # 목표가 도달, +10% 수익
            elif profit >= 0.05:  # +5~10%
                win_count += 1
                total_profit += profit  # 일부 수익
            else:  # 손절
                lose_count += 1
                total_profit -= 0.02  # -2% 손절
        
        # 통계
        total_trades = len(df_trade)
        win_rate = win_count / total_trades * 100
        avg_profit = total_profit / total_trades * 100
        
        print("=" * 60)
        print("백테스트 결과")
        print("=" * 60)
        print(f"총 거래: {total_trades}회")
        print(f"성공: {win_count}회")
        print(f"실패: {lose_count}회")
        print(f"승률: {win_rate:.1f}%")
        print(f"평균 수익: {avg_profit:+.2f}%")
        print(f"총 수익률: {total_profit*100:+.1f}%")
        
        # 실전 수익 추정
        initial_capital = 10000000  # 1천만원
        position_size = 1000000     # 1회 100만원
        
        estimated_profit = total_profit * position_size * total_trades
        final_capital = initial_capital + estimated_profit
        
        print(f"\n실전 추정 (초기 자본 1,000만원, 1회 100만원):")
        print(f"   예상 수익: {estimated_profit:+,.0f}원")
        print(f"   최종 자본: {final_capital:,.0f}원")
        print(f"   수익률: {estimated_profit/initial_capital*100:+.1f}%")
        print("=" * 60 + "\n")
    
    # =========================================
    # 5. 모델 저장
    # =========================================
    
    def save_model(self, output_dir='./models'):
        """모델 저장"""
        if self.model is None:
            print("❌ 저장할 모델이 없습니다.")
            return
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 모델 저장
        model_path = output_dir / 'crash_rebound_model.txt'
        self.model.save_model(str(model_path))
        print(f"✅ 모델 저장: {model_path}")
        
        # Feature 중요도 저장
        if self.feature_importance is not None:
            importance_path = output_dir / 'feature_importance.csv'
            self.feature_importance.to_csv(importance_path, index=False)
            print(f"✅ Feature 중요도 저장: {importance_path}\n")
    
    # =========================================
    # 6. 실행
    # =========================================
    
    def run(self):
        """전체 프로세스 실행"""
        # 1. 데이터 로드
        df = self.load_data()
        
        # 2. Feature 준비
        X, y, df_crash = self.prepare_features(df)
        
        # 3. 모델 학습
        X_train, X_test, y_train, y_test = self.train(X, y)
        
        # 4. 모델 평가
        y_pred_proba = self.evaluate(X_test, y_test)
        
        # 5. Feature 중요도
        self.analyze_feature_importance()
        
        # 6. 수익 시뮬레이션
        self.simulate_profit(df_crash, y_pred_proba, threshold=0.6)
        
        # 7. 모델 저장
        self.save_model()
        
        print("\n" + "="*60)
        print("🎉 모델 학습 완료!")
        print("="*60)


def main():
    """실행"""
    model = CrashReboundModel()
    model.run()


if __name__ == '__main__':
    main()
