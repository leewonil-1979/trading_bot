"""
실시간 급락 데이터 수집 → 자동 학습 업데이트 시스템

작동 방식:
1. 장중 실시간 급락 감지 (WebSocket)
2. 급락 데이터 저장 (일별)
3. 매일 장마감 후 학습 데이터 병합
4. AI 모델 재학습 (주간 단위)
5. 최적 익절/손절 동적 계산
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
from typing import Dict, List, Tuple, Optional
import FinanceDataReader as fdr
from pykrx import stock
import ta

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'crash_rebound'
REALTIME_DIR = PROJECT_ROOT / 'data' / 'realtime_crashes'
MODEL_DIR = PROJECT_ROOT / 'models'


class RealtimeLearningUpdater:
    """실시간 학습 데이터 업데이트 및 모델 최적화"""
    
    def __init__(self):
        self.crash_threshold = -10.0  # 급락 기준: -10% 이상
        self.realtime_dir = REALTIME_DIR
        self.realtime_dir.mkdir(parents=True, exist_ok=True)
        
        # 기존 학습 데이터 경로
        self.main_data_path = DATA_DIR / 'all_stocks_3years.parquet'
        
        # 실시간 수집 통계
        self.daily_crashes: List[Dict] = []
        
    # =========================================
    # 1. 실시간 급락 감지 및 저장
    # =========================================
    
    def detect_realtime_crash(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """
        실시간 급락 감지 (장중 호출)
        
        Returns:
            급락 데이터 dict 또는 None
        """
        try:
            # 오늘 + 최근 30일 데이터
            today = datetime.now()
            start_date = today - timedelta(days=30)
            
            df = fdr.DataReader(stock_code, start_date)
            
            if len(df) < 2:
                return None
            
            # 오늘 데이터
            latest = df.iloc[-1]
            prev_close = df.iloc[-2]['Close'] if len(df) >= 2 else latest['Open']
            
            # 급락률 계산
            crash_rate = (latest['Close'] - prev_close) / prev_close * 100
            
            # 급락 기준 체크
            if crash_rate <= self.crash_threshold:
                
                # 투자자 매매 데이터
                investor_data = self._get_investor_data(stock_code, today)
                
                # 기술적 지표
                technical = self._calculate_technical_indicators(df)
                
                crash_info = {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'Date': today,
                    'crash_rate': crash_rate,
                    'Open': float(latest['Open']),
                    'High': float(latest['High']),
                    'Low': float(latest['Low']),
                    'Close': float(latest['Close']),
                    'Volume': int(latest['Volume']),
                    **technical,
                    **investor_data
                }
                
                print(f"🚨 실시간 급락 감지: [{stock_name}] {crash_rate:.1f}%")
                
                return crash_info
            
            return None
            
        except Exception as e:
            print(f"급락 감지 오류 [{stock_code}]: {e}")
            return None
    
    def _get_investor_data(self, stock_code: str, date: datetime) -> Dict:
        """투자자별 매매 데이터 (7개 카테고리)"""
        try:
            date_str = date.strftime('%Y%m%d')
            
            # 투자자 매매 (기관, 외국인, 개인)
            df_trading = stock.get_market_trading_value_by_date(
                date_str, date_str, stock_code
            )
            
            # 세부 투자자 (금융투자, 보험, 투신 등)
            market = 'KOSPI' if stock_code.startswith(('0', '1', '2', '3', '4')) else 'KOSDAQ'
            df_detailed = stock.get_market_trading_value_by_investor(
                date_str, stock_code, market
            )
            
            result = {}
            
            # 기본 투자자 (기관, 외국인, 개인)
            if not df_trading.empty:
                latest = df_trading.iloc[-1] if len(df_trading) > 0 else None
                if latest is not None:
                    result['institution_net'] = int(latest.get('기관합계', 0))  # type: ignore
                    result['foreign_net'] = int(latest.get('외국인합계', 0))  # type: ignore
                    result['individual_net'] = int(latest.get('개인', 0))  # type: ignore
            
            # 세부 투자자 (7개 카테고리)
            if not df_detailed.empty:
                result['financial_invest_net'] = int(df_detailed.loc['금융투자', '순매수']) if '금융투자' in df_detailed.index else 0  # type: ignore
                result['insurance_net'] = int(df_detailed.loc['보험', '순매수']) if '보험' in df_detailed.index else 0  # type: ignore
                result['fund_net'] = int(df_detailed.loc['투신', '순매수']) if '투신' in df_detailed.index else 0  # type: ignore
                result['private_fund_net'] = int(df_detailed.loc['사모', '순매수']) if '사모' in df_detailed.index else 0  # type: ignore
                result['bank_net'] = int(df_detailed.loc['은행', '순매수']) if '은행' in df_detailed.index else 0  # type: ignore
                result['other_finance_net'] = int(df_detailed.loc['기타금융', '순매수']) if '기타금융' in df_detailed.index else 0  # type: ignore
                result['pension_net'] = int(df_detailed.loc['연기금 등', '순매수']) if '연기금 등' in df_detailed.index else 0  # type: ignore
            
            # 기본값 설정 (누락 시)
            for key in ['institution_net', 'foreign_net', 'individual_net',
                       'financial_invest_net', 'insurance_net', 'fund_net',
                       'private_fund_net', 'bank_net', 'other_finance_net', 'pension_net']:
                if key not in result:
                    result[key] = 0
            
            return result
            
        except Exception as e:
            print(f"투자자 데이터 오류: {e}")
            # 기본값 반환
            return {
                'institution_net': 0, 'foreign_net': 0, 'individual_net': 0,
                'financial_invest_net': 0, 'insurance_net': 0, 'fund_net': 0,
                'private_fund_net': 0, 'bank_net': 0, 'other_finance_net': 0,
                'pension_net': 0
            }
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """기술적 지표 계산 (24개)"""
        try:
            if len(df) < 20:
                return {}
            
            # 컬럼명 통일 (소문자 → 대문자)
            df_copy = df.copy()
            if 'close' in df_copy.columns:
                df_copy = df_copy.rename(columns={
                    'close': 'Close',
                    'high': 'High',
                    'low': 'Low',
                    'open': 'Open',
                    'volume': 'Volume'
                })
            
            close = df_copy['Close']
            high = df_copy['High']
            low = df_copy['Low']
            volume = df_copy['Volume']
            
            # 1. 이동평균
            sma_5 = close.rolling(5).mean().iloc[-1]
            sma_20 = close.rolling(20).mean().iloc[-1]
            
            # 2. RSI
            rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]  # type: ignore
            
            # 3. MACD
            macd_ind = ta.trend.MACD(close)  # type: ignore
            macd = macd_ind.macd().iloc[-1]
            macd_signal = macd_ind.macd_signal().iloc[-1]
            macd_diff = macd_ind.macd_diff().iloc[-1]
            
            # 4. 볼린저 밴드
            bb = ta.volatility.BollingerBands(close)  # type: ignore
            bb_upper = bb.bollinger_hband().iloc[-1]
            bb_middle = bb.bollinger_mavg().iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]
            bb_width = (bb_upper - bb_lower) / bb_middle * 100
            
            # 5. Stochastic
            stoch = ta.momentum.StochasticOscillator(high, low, close)  # type: ignore
            stoch_k = stoch.stoch().iloc[-1]
            stoch_d = stoch.stoch_signal().iloc[-1]
            
            # 6. ATR (변동성)
            atr = ta.volatility.AverageTrueRange(high, low, close).average_true_range().iloc[-1]  # type: ignore
            
            # 7. 거래량 지표
            volume_ma20 = volume.rolling(20).mean().iloc[-1]
            volume_spike = volume.iloc[-1] / volume_ma20 if volume_ma20 > 0 else 1.0
            
            # 8. 가격 변화율
            price_change_5d = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100 if len(close) > 5 else 0
            price_change_20d = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21] * 100 if len(close) > 20 else 0
            
            return {
                'sma_5': float(sma_5),
                'sma_20': float(sma_20),
                'rsi': float(rsi),
                'macd': float(macd),
                'macd_signal': float(macd_signal),
                'macd_diff': float(macd_diff),
                'bb_upper': float(bb_upper),
                'bb_middle': float(bb_middle),
                'bb_lower': float(bb_lower),
                'bb_width': float(bb_width),
                'stoch_k': float(stoch_k),
                'stoch_d': float(stoch_d),
                'atr': float(atr),
                'volume_ma20': float(volume_ma20),
                'volume_spike': float(volume_spike),
                'price_change_5d': float(price_change_5d),
                'price_change_20d': float(price_change_20d)
            }
            
        except Exception as e:
            print(f"기술적 지표 계산 오류: {e}")
            return {}
    
    def save_daily_crash(self, crash_data: Dict):
        """일별 급락 데이터 저장"""
        today = datetime.now().strftime('%Y%m%d')
        daily_file = self.realtime_dir / f'crash_{today}.parquet'
        
        # 기존 데이터 로드 (있으면)
        if daily_file.exists():
            df_existing = pd.read_parquet(daily_file)
            df_new = pd.DataFrame([crash_data])
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = pd.DataFrame([crash_data])
        
        # 저장
        df_combined.to_parquet(daily_file, index=False)
        print(f"💾 급락 데이터 저장: {daily_file.name} (총 {len(df_combined)}건)")
    
    # =========================================
    # 2. 학습 데이터 병합 (매일 장마감 후)
    # =========================================
    
    def merge_realtime_to_training_data(self):
        """실시간 수집 데이터를 기존 학습 데이터에 병합"""
        print("\n" + "="*70)
        print("📦 실시간 데이터 → 학습 데이터 병합")
        print("="*70 + "\n")
        
        # 1. 기존 학습 데이터 로드
        if not self.main_data_path.exists():
            print("❌ 기존 학습 데이터 없음")
            return
        
        df_main = pd.read_parquet(self.main_data_path)
        print(f"📊 기존 학습 데이터: {len(df_main):,}개 (크기: {self.main_data_path.stat().st_size / 1024**2:.1f}MB)")
        
        # 2. 실시간 데이터 수집
        realtime_files = list(self.realtime_dir.glob('crash_*.parquet'))
        
        if not realtime_files:
            print("ℹ️  병합할 실시간 데이터 없음")
            return
        
        # 3. 실시간 데이터 병합
        df_realtime_list = []
        for file in realtime_files:
            df_temp = pd.read_parquet(file)
            df_realtime_list.append(df_temp)
        
        df_realtime = pd.concat(df_realtime_list, ignore_index=True)
        print(f"📡 실시간 데이터: {len(df_realtime):,}개 (파일 {len(realtime_files)}개)")
        
        # 4. 데이터 통합
        df_combined = pd.concat([df_main, df_realtime], ignore_index=True)
        
        # 5. 중복 제거 (같은 종목, 같은 날짜)
        df_combined = df_combined.drop_duplicates(subset=['stock_code', 'Date'], keep='last')
        df_combined = df_combined.sort_values(['stock_code', 'Date']).reset_index(drop=True)
        
        print(f"✅ 통합 데이터: {len(df_combined):,}개 (중복 제거)")
        
        # 6. 백업 (기존 데이터)
        backup_path = self.main_data_path.with_name(
            f'all_stocks_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.parquet'
        )
        df_main.to_parquet(backup_path, index=False)
        print(f"💾 백업 저장: {backup_path.name}")
        
        # 7. 새 데이터 저장
        df_combined.to_parquet(self.main_data_path, index=False)
        new_size = self.main_data_path.stat().st_size / 1024**2
        print(f"💾 학습 데이터 업데이트: {new_size:.1f}MB")
        
        # 8. 실시간 데이터 아카이브
        archive_dir = self.realtime_dir / 'archived'
        archive_dir.mkdir(exist_ok=True)
        
        for file in realtime_files:
            file.rename(archive_dir / file.name)
        
        print(f"📁 실시간 데이터 아카이브: {len(realtime_files)}개 파일")
        
        print("\n✅ 데이터 병합 완료!\n")
        
        return df_combined
    
    # =========================================
    # 3. 종목별 최적 익절/손절 계산
    # =========================================
    
    def calculate_optimal_exit_points(
        self, 
        stock_code: str, 
        crash_data: Dict
    ) -> Tuple[float, float, float]:
        """
        종목별 최적 익절/손절 계산
        
        Returns:
            (목표_익절률, 손절률, 추가매수_시점)
        """
        try:
            # 1. 과거 급락 이력 조회
            df_history = self._get_crash_history(stock_code)
            
            if df_history.empty:
                # 과거 이력 없으면 기본값
                return (8.0, -5.0, -3.0)
            
            # 2. 급락 후 최대 수익률 분석
            max_returns = []
            for idx, row in df_history.iterrows():
                crash_date = pd.to_datetime(row['Date'])
                max_return = self._get_max_return_after_crash(
                    stock_code, 
                    crash_date, 
                    row['Close']
                )
                if max_return:
                    max_returns.append(max_return)
            
            if not max_returns:
                return (8.0, -5.0, -3.0)
            
            # 3. 통계 분석
            max_returns_arr = np.array(max_returns)
            
            # 75 percentile (상위 25% 수익률)
            target_profit = np.percentile(max_returns_arr, 75)
            target_profit = max(5.0, min(target_profit, 20.0))  # 5~20% 범위
            
            # 손절: -5% 고정 (안전)
            stop_loss = -5.0
            
            # 추가 매수: 평균 최저점 분석
            avg_lowest = self._get_average_lowest_point(stock_code, df_history)
            additional_buy = max(-5.0, min(avg_lowest, -2.0))  # -5% ~ -2%
            
            print(f"\n📊 [{stock_code}] 최적화 결과:")
            print(f"   목표 익절: +{target_profit:.1f}%")
            print(f"   손절: {stop_loss:.1f}%")
            print(f"   추가 매수: {additional_buy:.1f}%")
            
            return (float(target_profit), float(stop_loss), float(additional_buy))
            
        except Exception as e:
            print(f"최적화 오류 [{stock_code}]: {e}")
            return (8.0, -5.0, -3.0)
    
    def _get_crash_history(self, stock_code: str) -> pd.DataFrame:
        """종목의 과거 급락 이력"""
        try:
            # 통합 파일에서 검색
            if self.main_data_path.exists():
                df_main = pd.read_parquet(self.main_data_path)
                df_stock = df_main[
                    (df_main['stock_code'] == stock_code) & 
                    (df_main['crash_rate'] <= -10.0)
                ]
                
                # 컬럼명 통일 (소문자 → 대문자)
                if 'close' in df_stock.columns:
                    df_stock = df_stock.rename(columns={
                        'close': 'Close',
                        'high': 'High',
                        'low': 'Low',
                        'open': 'Open',
                        'volume': 'Volume'
                    })
                
                return df_stock
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"이력 조회 오류: {e}")
            return pd.DataFrame()
    
    def _get_max_return_after_crash(
        self, 
        stock_code: str, 
        crash_date: datetime, 
        crash_price: float
    ) -> Optional[float]:
        """급락 후 최대 수익률 계산 (5일간)"""
        try:
            # 급락일 이후 5일 데이터
            start = crash_date
            end = crash_date + timedelta(days=10)
            
            df = fdr.DataReader(stock_code, start, end)
            
            if len(df) < 2:
                return None
            
            # 컬럼명 통일
            if 'High' not in df.columns and 'high' in df.columns:
                df = df.rename(columns={'high': 'High'})
            
            # 최고가 대비 수익률
            max_high = df['High'].max()
            max_return = (max_high - crash_price) / crash_price * 100
            
            return float(max_return)
            
        except Exception as e:
            return None
    
    def _get_average_lowest_point(
        self, 
        stock_code: str, 
        df_history: pd.DataFrame
    ) -> float:
        """급락 후 평균 최저점"""
        try:
            lowest_points = []
            
            for idx, row in df_history.iterrows():
                crash_date = pd.to_datetime(row['Date'])
                crash_price = row.get('Close', row.get('close', 0))
                
                # 급락일 + 3일간 최저가
                end_date = crash_date + timedelta(days=5)
                df_after = fdr.DataReader(stock_code, crash_date, end_date)
                
                if len(df_after) > 0:
                    # 컬럼명 통일
                    if 'Low' not in df_after.columns and 'low' in df_after.columns:
                        df_after = df_after.rename(columns={'low': 'Low'})
                    
                    lowest = df_after['Low'].min()
                    drop_rate = (lowest - crash_price) / crash_price * 100
                    lowest_points.append(drop_rate)
            
            if lowest_points:
                return float(np.mean(lowest_points))
            
            return -3.0
            
        except Exception as e:
            return -3.0


# =========================================
# 실행 예제
# =========================================

def main():
    """테스트 실행"""
    updater = RealtimeLearningUpdater()
    
    # 1. 급락 감지 테스트
    print("\n🔍 급락 감지 테스트\n")
    test_stocks = [
        ('005930', '삼성전자'),
        ('000660', 'SK하이닉스'),
    ]
    
    for code, name in test_stocks:
        crash = updater.detect_realtime_crash(code, name)
        if crash:
            updater.save_daily_crash(crash)
    
    # 2. 데이터 병합 테스트
    print("\n" + "="*70)
    updater.merge_realtime_to_training_data()
    
    # 3. 최적화 테스트
    print("\n" + "="*70)
    print("🎯 최적 익절/손절 계산 테스트\n")
    
    for code, name in test_stocks:
        profit, loss, add_buy = updater.calculate_optimal_exit_points(
            code, 
            {'Close': 70000}
        )
        print(f"\n[{name}] 익절: +{profit:.1f}% | 손절: {loss:.1f}% | 추가매수: {add_buy:.1f}%")


if __name__ == '__main__':
    main()
