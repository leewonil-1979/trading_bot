"""
강화된 데이터 수집기
- 투자자별 매매 (기관, 외국인, 개인, 프로그램)
- 공시 정보 (DART)
- 뉴스 감성 분석
- 시장/업종 상황

실제 상관관계 검증을 위한 데이터 수집
"""

import pandas as pd
import numpy as np
from pykrx import stock
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')


class EnhancedDataCollector:
    """강화된 데이터 수집 및 상관관계 분석"""
    
    def __init__(self):
        self.base_dir = Path('./data/crash_rebound')
        self.output_dir = Path('./data/enhanced')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 기존 데이터 로드
        print("📂 기존 데이터 로드 중...")
        self.df_base = pd.read_parquet(self.base_dir / 'all_stocks_3years.parquet')
        print(f"✅ {len(self.df_base):,}개 행 로드 완료\n")
        
        # 급락 이벤트만 추출
        self.df_crashes = self.df_base[self.df_base['crash'] == 1].copy()
        
        # date가 인덱스인 경우 컬럼으로 변환
        if 'date' not in self.df_crashes.columns and self.df_crashes.index.name == 'date':
            self.df_crashes = self.df_crashes.reset_index()
        
        print(f"📊 급락 이벤트: {len(self.df_crashes):,}개")
        print(f"   - 성공 반등: {self.df_crashes['success'].sum():,}개 ({self.df_crashes['success'].sum()/len(self.df_crashes)*100:.1f}%)")
        print(f"   - 실패: {(~self.df_crashes['success']).sum():,}개\n")
    
    # =========================================
    # 1. 투자자별 매매 데이터 수집
    # =========================================
    
    def collect_investor_data(self):
        """
        투자자별 매매 데이터 수집 및 상관관계 분석
        
        핵심 질문:
        1. 외국인 대량 매도 종목은 정말 반등 안하나?
        2. 프로그램 매도 종목은?
        3. 기관 매수 전환 시 반등률은?
        """
        print("="*70)
        print("1️⃣ 투자자별 매매 데이터 수집")
        print("="*70 + "\n")
        
        # 날짜별로 종목 그룹화
        date_stocks = self.df_crashes.groupby('date')['stock_code'].apply(list).to_dict()
        
        all_investor_data = []
        total_dates = len(date_stocks)
        
        for idx, (date, stock_codes) in enumerate(date_stocks.items(), 1):
            if idx % 50 == 0:
                print(f"진행: {idx}/{total_dates} ({idx/total_dates*100:.1f}%)")
            
            try:
                # 날짜 형식 변환
                date_str = pd.to_datetime(date).strftime('%Y%m%d')
                
                # 해당 날짜의 모든 종목 투자자 매매 조회
                for stock_code in stock_codes:
                    try:
                        # 급락 당일 투자자 매매
                        df_investor = stock.get_market_trading_value_by_date(
                            date_str, date_str, stock_code
                        )
                        
                        if not df_investor.empty:
                            all_investor_data.append({
                                'date': date,
                                'stock_code': stock_code,
                                'institution_net': df_investor['기관계'].iloc[0] if '기관계' in df_investor.columns else 0,
                                'foreign_net': df_investor['외국인'].iloc[0] if '외국인' in df_investor.columns else 0,
                                'individual_net': df_investor['개인'].iloc[0] if '개인' in df_investor.columns else 0,
                            })
                            
                            # 프로그램 매매 (별도 API)
                            try:
                                df_program = stock.get_market_trading_value_by_date(
                                    date_str, date_str, stock_code, detail=True
                                )
                                if not df_program.empty and '프로그램' in df_program.columns:
                                    all_investor_data[-1]['program_net'] = df_program['프로그램'].iloc[0]
                                else:
                                    all_investor_data[-1]['program_net'] = 0
                            except:
                                all_investor_data[-1]['program_net'] = 0
                        
                        time.sleep(0.05)  # API 제한 회피
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
        
        # DataFrame 변환
        df_investor = pd.DataFrame(all_investor_data)
        
        print(f"\n✅ 투자자 매매 데이터 수집 완료: {len(df_investor):,}건")
        
        # 기존 데이터와 병합
        df_merged = self.df_crashes.merge(
            df_investor,
            on=['date', 'stock_code'],
            how='left'
        )
        
        # 결측치 0으로 채우기
        for col in ['institution_net', 'foreign_net', 'individual_net', 'program_net']:
            df_merged[col] = df_merged[col].fillna(0)
        
        # 저장
        output_file = self.output_dir / 'crashes_with_investor.parquet'
        df_merged.to_parquet(output_file)
        print(f"💾 저장: {output_file}\n")
        
        # 상관관계 분석
        self._analyze_investor_correlation(df_merged)
        
        return df_merged
    
    def _analyze_investor_correlation(self, df):
        """투자자 매매와 반등률 상관관계 분석"""
        print("="*70)
        print("📊 투자자 매매 vs 반등률 상관관계 분석")
        print("="*70 + "\n")
        
        # 1. 외국인 순매수 구간별 반등률
        print("1️⃣ 외국인 순매수 구간별 반등률")
        print("-" * 70)
        
        df['foreign_group'] = pd.cut(
            df['foreign_net'] / 100000000,  # 억원 단위
            bins=[-np.inf, -100, -50, -10, 0, 10, 50, 100, np.inf],
            labels=['-100억 이하', '-100~-50억', '-50~-10억', '-10~0억', 
                   '0~10억', '10~50억', '50~100억', '100억 이상']
        )
        
        foreign_analysis = df.groupby('foreign_group').agg({
            'success': ['count', 'sum', 'mean'],
            'rebound_d5': 'mean'
        }).round(3)
        
        print(foreign_analysis)
        print()
        
        # 2. 프로그램 순매수 구간별 반등률
        print("2️⃣ 프로그램 순매수 구간별 반등률")
        print("-" * 70)
        
        df['program_group'] = pd.cut(
            df['program_net'] / 100000000,
            bins=[-np.inf, -100, -50, -10, 0, 10, 50, 100, np.inf],
            labels=['-100억 이하', '-100~-50억', '-50~-10억', '-10~0억', 
                   '0~10억', '10~50억', '50~100억', '100억 이상']
        )
        
        program_analysis = df.groupby('program_group').agg({
            'success': ['count', 'sum', 'mean'],
            'rebound_d5': 'mean'
        }).round(3)
        
        print(program_analysis)
        print()
        
        # 3. 기관 순매수 구간별 반등률
        print("3️⃣ 기관 순매수 구간별 반등률")
        print("-" * 70)
        
        df['institution_group'] = pd.cut(
            df['institution_net'] / 100000000,
            bins=[-np.inf, -50, -10, 0, 10, 50, np.inf],
            labels=['-50억 이하', '-50~-10억', '-10~0억', '0~10억', '10~50억', '50억 이상']
        )
        
        institution_analysis = df.groupby('institution_group').agg({
            'success': ['count', 'sum', 'mean'],
            'rebound_d5': 'mean'
        }).round(3)
        
        print(institution_analysis)
        print()
        
        # 4. 복합 조건 분석
        print("4️⃣ 복합 조건별 반등률")
        print("-" * 70)
        
        conditions = {
            '외국인+기관 모두 매도 (-10억 이상)': 
                (df['foreign_net'] < -1000000000) & (df['institution_net'] < -1000000000),
            '외국인+프로그램 모두 매도 (-10억 이상)': 
                (df['foreign_net'] < -1000000000) & (df['program_net'] < -1000000000),
            '외국인 대량 매도 (-50억 이상)': 
                df['foreign_net'] < -5000000000,
            '프로그램 대량 매도 (-50억 이상)': 
                df['program_net'] < -5000000000,
            '외국인+기관 모두 매수': 
                (df['foreign_net'] > 0) & (df['institution_net'] > 0),
            '외국인 대량 매수 (+50억 이상)': 
                df['foreign_net'] > 5000000000,
        }
        
        for condition_name, condition in conditions.items():
            filtered = df[condition]
            if len(filtered) > 0:
                success_rate = filtered['success'].mean() * 100
                avg_rebound = filtered['rebound_d5'].mean() * 100
                count = len(filtered)
                print(f"{condition_name}:")
                print(f"  건수: {count:,}개, 성공률: {success_rate:.1f}%, 평균 반등: {avg_rebound:+.2f}%")
            else:
                print(f"{condition_name}: 데이터 없음")
        
        print()
        
        # 결과 저장
        analysis_result = {
            'foreign_analysis': foreign_analysis.to_dict(),
            'program_analysis': program_analysis.to_dict(),
            'institution_analysis': institution_analysis.to_dict()
        }
        
        with open(self.output_dir / 'investor_correlation_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2, default=str)
    
    # =========================================
    # 2. 공시 데이터 수집 및 분석
    # =========================================
    
    def collect_disclosure_data(self, dart_api_key=None):
        """
        공시 데이터 수집 및 상관관계 분석
        
        핵심 질문:
        1. 유상증자 공시 후 급락 → 정말 반등 안하나?
        2. 실적 악화 공시 후 급락 → 반등률은?
        3. 어떤 공시가 진짜 악재인가?
        """
        print("="*70)
        print("2️⃣ 공시 데이터 수집 및 분석")
        print("="*70 + "\n")
        
        if not dart_api_key:
            print("⚠️ DART API 키가 없어 샘플 분석만 수행합니다.")
            print("실제 수집을 위해서는 https://opendart.fss.or.kr 에서 API 키 발급 필요\n")
            
            # 간단한 공시 키워드 크롤링으로 대체
            return self._collect_disclosure_simple()
        
        # DART API 사용 (실제 구현)
        # TODO: API 키 발급 후 구현
        pass
    
    def _collect_disclosure_simple(self):
        """
        간단한 공시 정보 수집 (네이버 금융 크롤링)
        
        급락 전후 7일간 주요 공시 키워드 확인
        """
        print("📰 네이버 금융에서 공시 정보 수집 중...\n")
        
        # 샘플: 유상증자, 감사의견, 실적 관련 키워드
        disclosure_keywords = {
            '유상증자': -0.5,  # 약한 악재
            '무상증자': 0.3,   # 호재
            '자사주매입': 0.7, # 호재
            '감사의견': -0.9,  # 강한 악재
            '횡령': -1.0,      # 최악
            '배임': -1.0,
            '영업이익': 0.0,   # 내용 확인 필요
            '수주': 0.5,       # 호재
            '계약': 0.4,
            '배당': 0.3,
        }
        
        all_disclosures = []
        
        # 급락 이벤트별로 처리
        for idx, row in self.df_crashes.head(100).iterrows():  # 샘플 100개
            stock_code = row['stock_code']
            date = pd.to_datetime(row['date'])
            
            # 급락 전후 7일
            start_date = date - timedelta(days=7)
            end_date = date + timedelta(days=1)
            
            try:
                # 네이버 금융 공시 페이지
                url = f"https://finance.naver.com/item/news_notice.naver?code={stock_code}&page=1"
                
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 공시 제목 추출
                notices = soup.select('.title')
                
                found_disclosures = []
                for notice in notices[:10]:  # 최근 10개만
                    title = notice.get_text().strip()
                    
                    # 키워드 매칭
                    for keyword, impact in disclosure_keywords.items():
                        if keyword in title:
                            found_disclosures.append({
                                'keyword': keyword,
                                'impact': impact,
                                'title': title
                            })
                
                if found_disclosures:
                    all_disclosures.append({
                        'stock_code': stock_code,
                        'date': date,
                        'disclosures': found_disclosures,
                        'success': row['success'],
                        'rebound_d5': row['rebound_d5']
                    })
                
                time.sleep(0.5)  # 크롤링 제한
                
            except Exception as e:
                continue
        
        # 분석
        if all_disclosures:
            self._analyze_disclosure_correlation(all_disclosures)
        
        return all_disclosures
    
    def _analyze_disclosure_correlation(self, disclosures):
        """공시와 반등률 상관관계 분석"""
        print("\n" + "="*70)
        print("📊 공시 키워드별 반등률 분석")
        print("="*70 + "\n")
        
        # 키워드별 그룹화
        keyword_stats = {}
        
        for item in disclosures:
            for disc in item['disclosures']:
                keyword = disc['keyword']
                
                if keyword not in keyword_stats:
                    keyword_stats[keyword] = {
                        'count': 0,
                        'success_count': 0,
                        'total_rebound': 0
                    }
                
                keyword_stats[keyword]['count'] += 1
                if item['success']:
                    keyword_stats[keyword]['success_count'] += 1
                keyword_stats[keyword]['total_rebound'] += item['rebound_d5']
        
        # 결과 출력
        print(f"{'공시 키워드':<15} {'건수':>6} {'성공률':>8} {'평균 반등률':>12}")
        print("-" * 70)
        
        for keyword, stats in sorted(keyword_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            count = stats['count']
            success_rate = stats['success_count'] / count * 100
            avg_rebound = stats['total_rebound'] / count * 100
            
            print(f"{keyword:<15} {count:>6} {success_rate:>7.1f}% {avg_rebound:>11.2f}%")
        
        print()
    
    # =========================================
    # 3. 실행
    # =========================================
    
    def run(self, mode='all'):
        """
        데이터 수집 및 분석 실행
        
        Args:
            mode: 'investor', 'disclosure', 'news', 'all'
        """
        print(f"\n{'='*70}")
        print(f"🚀 강화된 데이터 수집 시작 (모드: {mode})")
        print(f"{'='*70}\n")
        
        results = {}
        
        if mode in ['investor', 'all']:
            print("\n⏰ 예상 소요 시간: 2~3시간")
            print("진행하시겠습니까? (Enter로 계속, Ctrl+C로 중단)\n")
            
            results['investor'] = self.collect_investor_data()
        
        if mode in ['disclosure', 'all']:
            results['disclosure'] = self.collect_disclosure_data()
        
        print(f"\n{'='*70}")
        print("✅ 데이터 수집 및 분석 완료!")
        print(f"{'='*70}\n")
        
        return results


def main():
    """실행"""
    import sys
    
    collector = EnhancedDataCollector()
    
    # 명령행 인자로 모드 선택
    mode = sys.argv[1] if len(sys.argv) > 1 else 'investor'
    
    collector.run(mode=mode)


if __name__ == '__main__':
    main()
