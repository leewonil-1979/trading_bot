"""
급락 후 반등 전략 - 3년 학습 데이터 수집기
시간외 거래 제외, 모든 데이터 시계열 매칭

수집 데이터:
1. 일봉 데이터 (시가, 고가, 저가, 종가, 거래량, 거래대금)
2. 투자자별 매매 (기관, 외국인, 개인, 프로그램)
3. 뉴스 (제목, 감성 점수)
4. 공시 (제목, 영향도)
5. 기술적 지표 (RSI, MACD, 볼린저밴드 등)
6. 급락/반등 라벨 (정답)
"""

import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from pykrx import stock
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ta
import time
import json
from pathlib import Path


class CrashReboundDataCollector:
    """3년간 급락-반등 데이터 수집"""
    
    def __init__(self, output_dir='./data/crash_rebound'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 날짜 범위 (3년)
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=365*3)
        
        print(f"\n{'='*60}")
        print(f"📊 급락-반등 데이터 수집기")
        print(f"기간: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        print(f"저장 경로: {self.output_dir}")
        print(f"{'='*60}\n")
    
    # =========================================
    # 1. 전체 종목 리스트
    # =========================================
    
    def get_all_stocks(self):
        """전체 상장 종목 리스트 (일반주 + 우선주 포함)"""
        print("📋 전체 종목 리스트 조회 중...")
        
        stocks = fdr.StockListing('KRX')
        
        # 스팩, 리츠만 제외 (우선주 포함!)
        stocks = stocks[
            (~stocks['Name'].str.contains('스팩')) &
            (~stocks['Name'].str.contains('리츠'))
        ]
        
        # 통계
        total = len(stocks)
        preferred = len(stocks[stocks['Code'].str.endswith('0')])
        common = total - preferred
        
        print(f"✅ 총 {total:,}개 종목")
        print(f"   - 일반주: {common:,}개")
        print(f"   - 우선주: {preferred:,}개\n")
        
        return stocks
    
    # =========================================
    # 2. 일봉 데이터 수집
    # =========================================
    
    def collect_price_data(self, stock_code, stock_name):
        """
        일봉 데이터 수집
        
        Returns:
            DataFrame with columns:
            - Date, Open, High, Low, Close, Volume, Change
        """
        try:
            df = fdr.DataReader(
                stock_code,
                self.start_date.strftime('%Y-%m-%d'),
                self.end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty:
                return None
            
            # 컬럼 정리
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Change': 'change_pct'
            })
            
            # 기본 정보 추가
            df['stock_code'] = stock_code
            df['stock_name'] = stock_name
            
            return df
            
        except Exception as e:
            print(f"   ⚠️ 일봉 수집 실패 [{stock_name}]: {e}")
            return None
    
    # =========================================
    # 3. 투자자별 매매 데이터
    # =========================================
    
    def collect_investor_trading(self, stock_code):
        """
        투자자별 매매 데이터 (기관, 외국인, 개인, 프로그램)
        
        Returns:
            DataFrame with columns:
            - Date, institution_net, foreign_net, individual_net, program_net
        """
        try:
            # 날짜 형식 변환
            start = self.start_date.strftime('%Y%m%d')
            end = self.end_date.strftime('%Y%m%d')
            
            # 투자자별 순매수 (수정된 컬럼명 사용)
            df_investor = stock.get_market_trading_value_by_date(
                start, end, stock_code
            )
            
            if df_investor.empty:
                return None
            
            # pykrx 반환 컬럼: 기관합계, 기타법인, 개인, 외국인합계
            # 컬럼 정리 (break 제거 - 모든 컬럼 매핑해야 함!)
            if '기관합계' in df_investor.columns:
                df_investor['institution_net'] = df_investor['기관합계']
            elif '기관' in df_investor.columns:
                df_investor['institution_net'] = df_investor['기관']
            else:
                df_investor['institution_net'] = 0
                
            if '외국인합계' in df_investor.columns:
                df_investor['foreign_net'] = df_investor['외국인합계']
            elif '외국인' in df_investor.columns:
                df_investor['foreign_net'] = df_investor['외국인']
            else:
                df_investor['foreign_net'] = 0
                
            if '개인' in df_investor.columns:
                df_investor['individual_net'] = df_investor['개인']
            else:
                df_investor['individual_net'] = 0
            
            # 프로그램 매매는 일단 0으로 (별도 API 필요)
            df_investor['program_net'] = 0
            
            return df_investor[['institution_net', 'foreign_net', 'individual_net', 'program_net']]
            
        except Exception as e:
            print(f"   ⚠️ 투자자 매매 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # =========================================
    # 4. 뉴스 데이터 (과거 뉴스는 제한적)
    # =========================================
    
    def collect_news_sentiment(self, stock_code, date_range):
        """
        뉴스 감성 분석 (일별 집계)
        
        Note: 네이버는 최근 뉴스만 제공하므로,
              과거 데이터는 제한적. 대신 일별 뉴스 개수와 평균 감성 점수만 추정
        
        Returns:
            DataFrame with columns:
            - Date, news_count, sentiment_score
        """
        # 과거 뉴스는 수집 어려움
        # 일단 더미 데이터로 채우고, 실시간 수집 시 업데이트
        
        news_data = pd.DataFrame({
            'date': date_range,
            'news_count': 0,
            'sentiment_score': 0.0  # -1 (악재) ~ +1 (호재)
        })
        news_data.set_index('date', inplace=True)
        
        return news_data
    
    # =========================================
    # 5. 공시 데이터 (DART)
    # =========================================
    
    def collect_disclosure(self, stock_code, corp_code, date_range):
        """
        공시 데이터 (일별 집계)
        
        Returns:
            DataFrame with columns:
            - Date, disclosure_count, disclosure_impact
        """
        # DART API는 별도 구현 필요
        # 일단 더미 데이터
        
        disclosure_data = pd.DataFrame({
            'date': date_range,
            'disclosure_count': 0,
            'disclosure_impact': 0.0  # -1 (악재) ~ +1 (호재)
        })
        disclosure_data.set_index('date', inplace=True)
        
        return disclosure_data
    
    # =========================================
    # 6. 기술적 지표
    # =========================================
    
    def calculate_technical_indicators(self, df):
        """
        기술적 지표 계산
        
        Adds columns:
        - RSI, MACD, MACD_signal, BB_upper, BB_middle, BB_lower
        - MA5, MA20, MA60
        - volume_ma20, volume_spike
        """
        if len(df) < 60:
            return df
        
        try:
            # 이동평균선
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            
            # 거래량 이동평균
            df['volume_ma20'] = df['volume'].rolling(20).mean()
            df['volume_spike'] = df['volume'] / df['volume_ma20']
            
            # RSI
            rsi_indicator = ta.momentum.RSIIndicator(df['close'])  # type: ignore
            df['rsi'] = rsi_indicator.rsi()
            
            # MACD
            macd_indicator = ta.trend.MACD(df['close'])  # type: ignore
            df['macd'] = macd_indicator.macd()
            df['macd_signal'] = macd_indicator.macd_signal()
            df['macd_diff'] = macd_indicator.macd_diff()
            
            # 볼린저 밴드
            bb_indicator = ta.volatility.BollingerBands(df['close'])  # type: ignore
            df['bb_upper'] = bb_indicator.bollinger_hband()
            df['bb_middle'] = bb_indicator.bollinger_mavg()
            df['bb_lower'] = bb_indicator.bollinger_lband()
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # 스토캠스틱
            stoch_indicator = ta.momentum.StochasticOscillator(  # type: ignore
                df['high'], df['low'], df['close']
            )
            df['stoch_k'] = stoch_indicator.stoch()
            df['stoch_d'] = stoch_indicator.stoch_signal()
            
            # ATR (변동성)
            atr_indicator = ta.volatility.AverageTrueRange(  # type: ignore
                df['high'], df['low'], df['close']
            )
            df['atr'] = atr_indicator.average_true_range()
            
        except Exception as e:
            print(f"   ⚠️ 기술적 지표 계산 실패: {e}")
        
        return df
    
    # =========================================
    # 7. 급락/반등 라벨 생성
    # =========================================
    
    def generate_labels(self, df):
        """
        급락 및 반등 라벨 생성
        
        Adds columns:
        - crash: 급락 여부 (1/0)
        - crash_rate: 급락률 (%)
        - rebound_d1: 다음날 반등률
        - rebound_d2: 2일 후 반등률
        - rebound_d5: 5일 후 최대 반등률
        - hold_days: 최대 반등까지 보유일수
        """
        # 일별 수익률
        df['daily_return'] = df['close'].pct_change() * 100
        
        # 급락 감지 (-10% 이상) - 더 많은 데이터 확보
        df['crash'] = (df['daily_return'] <= -10).astype(int)
        df['crash_rate'] = df['daily_return'].apply(lambda x: x if x <= -10 else 0)
        
        # 반등률 계산
        df['rebound_d1'] = df['close'].shift(-1) / df['close'] - 1  # 다음날
        df['rebound_d2'] = df['close'].shift(-2) / df['close'] - 1  # 2일 후
        
        # 5일간 최대 반등률
        rebound_d5_list = []
        hold_days_list = []
        
        for i in range(len(df)):
            if i + 5 >= len(df):
                rebound_d5_list.append(np.nan)
                hold_days_list.append(np.nan)
                continue
            
            # 5일간 최고가
            future_5d = df.iloc[i+1:i+6]
            max_price = future_5d['high'].max()
            max_return = (max_price / df.iloc[i]['close']) - 1
            
            # 최고가 도달 일수
            max_idx = future_5d['high'].argmax()
            hold_days = max_idx + 1
            
            rebound_d5_list.append(max_return)
            hold_days_list.append(hold_days)
        
        df['rebound_d5'] = rebound_d5_list
        df['hold_days'] = hold_days_list
        
        # 성공 라벨 (5일 내 +10% 이상 반등)
        df['success'] = ((df['rebound_d5'] >= 0.10) & (df['crash'] == 1)).astype(int)
        
        return df
    
    # =========================================
    # 8. 통합 데이터 수집
    # =========================================
    
    def collect_stock_data(self, stock_code, stock_name):
        """
        종목별 전체 데이터 수집 및 통합
        
        Returns:
            통합 DataFrame
        """
        print(f"\n{'='*60}")
        print(f"📊 [{stock_name}] ({stock_code}) 데이터 수집 중...")
        print(f"{'='*60}")
        
        # 1. 일봉 데이터
        print("1️⃣ 일봉 데이터...")
        df = self.collect_price_data(stock_code, stock_name)
        
        if df is None or len(df) < 100:
            print(f"   ⚠️ 데이터 부족 (최소 100일 필요)")
            return None
        
        print(f"   ✅ {len(df)}일 수집")
        
        # 2. 투자자별 매매
        print("2️⃣ 투자자별 매매...")
        df_investor = self.collect_investor_trading(stock_code)
        
        if df_investor is not None:
            df = df.join(df_investor, how='left')
            df[['institution_net', 'foreign_net', 'individual_net', 'program_net']] = \
                df[['institution_net', 'foreign_net', 'individual_net', 'program_net']].fillna(0)
            print(f"   ✅ 완료")
        else:
            print(f"   ⚠️ 투자자 매매 데이터 없음")
            df['institution_net'] = 0
            df['foreign_net'] = 0
            df['individual_net'] = 0
            df['program_net'] = 0
        
        # 3. 뉴스 감성 (더미)
        print("3️⃣ 뉴스 데이터 (더미)...")
        df_news = self.collect_news_sentiment(stock_code, df.index)
        df = df.join(df_news, how='left')
        print(f"   ✅ 완료 (실시간 수집 시 업데이트 필요)")
        
        # 4. 공시 (더미)
        print("4️⃣ 공시 데이터 (더미)...")
        df_disclosure = self.collect_disclosure(stock_code, None, df.index)
        df = df.join(df_disclosure, how='left')
        print(f"   ✅ 완료 (실시간 수집 시 업데이트 필요)")
        
        # 5. 기술적 지표
        print("5️⃣ 기술적 지표 계산...")
        df = self.calculate_technical_indicators(df)
        print(f"   ✅ 완료")
        
        # 6. 급락/반등 라벨
        print("6️⃣ 급락/반등 라벨 생성...")
        df = self.generate_labels(df)
        crash_count = df['crash'].sum()
        success_count = df['success'].sum()
        print(f"   ✅ 급락 {crash_count}회, 성공 반등 {success_count}회")
        
        # 7. 결측치 제거
        df = df.dropna()
        
        print(f"\n✅ 최종 데이터: {len(df)}일")
        
        return df
    
    # =========================================
    # 9. 전체 종목 일괄 수집
    # =========================================
    
    def _save_progress(self, progress_file, completed_codes):
        """진행 상황 저장"""
        progress = {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'completed_codes': list(completed_codes),
            'total_completed': len(completed_codes)
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    
    def collect_all_stocks(self, max_stocks=None, crash_only=True):
        """
        전체 종목 데이터 일괄 수집 (중단 후 이어서 가능)
        
        Args:
            max_stocks: 최대 수집 종목 수 (None=전체)
            crash_only: 급락이 있는 종목만 저장
        """
        stocks = self.get_all_stocks()
        
        if max_stocks:
            stocks = stocks.head(max_stocks)
        
        # 진행 상황 파일
        progress_file = self.output_dir / 'collection_progress.json'
        
        # 기존 진행 상황 확인
        completed_codes = set()
        if progress_file.exists():
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
                completed_codes = set(progress.get('completed_codes', []))
                print(f"📋 이전 진행: {len(completed_codes)}개 완료 → 이어서 수집\n")
        
        all_data = []
        crash_stocks_count = 0
        
        for idx, row in stocks.iterrows():
            stock_code = row['Code']
            stock_name = row['Name']
            
            # 이미 수집 완료된 종목 스킵
            if stock_code in completed_codes:
                print(f"[{idx+1}/{len(stocks)}] {stock_name} ({stock_code}) - ✅ 이미 완료")  # type: ignore
                continue
            
            print(f"\n[{idx+1}/{len(stocks)}] {stock_name} ({stock_code})")  # type: ignore
            
            # 데이터 수집
            df = self.collect_stock_data(stock_code, stock_name)
            
            if df is None:
                # 실패해도 진행 상황 저장 (무한 재시도 방지)
                completed_codes.add(stock_code)
                self._save_progress(progress_file, completed_codes)
                continue
            
            # 급락이 있는 종목만 저장
            if crash_only and df['crash'].sum() == 0:
                print(f"   ⚠️ 급락 이력 없음 → 스킵")
                completed_codes.add(stock_code)
                self._save_progress(progress_file, completed_codes)
                continue
            
            crash_stocks_count += 1
            all_data.append(df)
            
            # 개별 저장
            output_file = self.output_dir / f"{stock_code}_{stock_name}.parquet"
            df.to_parquet(output_file, compression='snappy')
            print(f"   💾 저장: {output_file}")
            
            # 진행 상황 저장
            completed_codes.add(stock_code)
            self._save_progress(progress_file, completed_codes)
            
            # API 호출 제한 (1초 대기)
            time.sleep(1)
        
        # 통합 데이터 저장
        print(f"\n{'='*60}")
        print(f"📦 통합 데이터 생성 중...")
        
        # 개별 파일들 모두 로드
        parquet_files = list(self.output_dir.glob("*.parquet"))
        parquet_files = [f for f in parquet_files if f.name != "all_stocks_3years.parquet"]
        
        print(f"   총 {len(parquet_files)}개 파일 병합...")
        
        all_data = []
        for pf in parquet_files:
            try:
                df = pd.read_parquet(pf)
                all_data.append(df)
            except:
                print(f"   ⚠️ {pf.name} 로드 실패")
        
        if all_data:
            df_all = pd.concat(all_data, ignore_index=True)
            
            output_file = self.output_dir / "all_stocks_3years.parquet"
            df_all.to_parquet(output_file, compression='snappy')
            
            print(f"✅ 통합 저장: {output_file}")
            print(f"   총 종목: {len(parquet_files)}개")
            print(f"   총 데이터: {len(df_all):,}행")
            print(f"   총 급락: {df_all['crash'].sum():,}회")
            print(f"   성공 반등: {df_all['success'].sum():,}회")
            print(f"{'='*60}\n")
            
            # 통계 저장
            stats = {
                'collection_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period': f"{self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}",
                'total_stocks': len(parquet_files),
                'total_rows': len(df_all),
                'total_crashes': int(df_all['crash'].sum()),
                'successful_rebounds': int(df_all['success'].sum()),
                'success_rate': float(df_all['success'].sum() / df_all['crash'].sum() * 100) if df_all['crash'].sum() > 0 else 0
            }
            
            with open(self.output_dir / 'collection_stats.json', 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            return df_all
        
        return None


# =========================================
# 실행
# =========================================

def main():
    """3년 데이터 수집 실행"""
    
    collector = CrashReboundDataCollector(output_dir='./data/crash_rebound')
    
    # 전체 종목 수집 (급락 있는 종목만)
    # max_stocks=100 → 테스트용 (전체는 None)
    df_all = collector.collect_all_stocks(
        max_stocks=None,  # None=전체, 100=상위 100개만
        crash_only=True   # 급락 이력 있는 종목만
    )
    
    if df_all is not None:
        print("\n🎉 데이터 수집 완료!")
        print(f"\n데이터 미리보기:")
        print(df_all.head(10))
        
        print(f"\n컬럼 목록:")
        print(df_all.columns.tolist())


if __name__ == '__main__':
    main()
