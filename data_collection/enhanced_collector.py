"""
추가 데이터 수집기
- 프로그램 매매 (네이버 증권)
- 공시 데이터 (DART API)
- 뉴스 데이터 (네이버 뉴스)
"""

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
import re


class EnhancedDataCollector:
    """추가 데이터 수집기"""
    
    def __init__(self, data_dir='./data/crash_rebound'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # DART API 키 (https://opendart.fss.or.kr/에서 발급 필요)
        self.dart_api_key = None
        
        # 진행상황 저장
        self.progress_file = self.data_dir / 'enhanced_progress.json'
        self.load_progress()
    
    def load_progress(self):
        """진행상황 로드"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                self.progress = json.load(f)
        else:
            self.progress = {'completed': []}
    
    def save_progress(self, stock_code):
        """진행상황 저장"""
        if stock_code not in self.progress['completed']:
            self.progress['completed'].append(stock_code)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f)
    
    # =========================================
    # 1. 프로그램 매매 데이터 (네이버 증권)
    # =========================================
    
    def collect_program_trading(self, stock_code, start_date, end_date):
        """프로그램 매매 데이터 수집 (네이버 증권)"""
        try:
            url = f"https://finance.naver.com/item/frgn.naver?code={stock_code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table', class_='type2')
            
            if len(tables) < 2:
                return None
            
            # 프로그램 매매 테이블
            table = tables[1]
            rows = table.find_all('tr')[2:]
            
            data = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 7:
                    continue
                
                try:
                    date_str = cols[0].text.strip()
                    if not date_str:
                        continue
                    
                    date = pd.to_datetime(date_str, format='%Y.%m.%d')
                    program_text = cols[6].text.strip().replace(',', '').replace('+', '')
                    program_net = int(program_text) if program_text else 0
                    
                    data.append({'Date': date, 'program_net': program_net})
                except:
                    continue
            
            if not data:
                return None
            
            df = pd.DataFrame(data).set_index('Date')
            df = df[(df.index >= pd.to_datetime(start_date)) & 
                   (df.index <= pd.to_datetime(end_date))]
            
            return df
            
        except Exception as e:
            print(f"   ⚠️ 프로그램 매매 수집 실패: {e}")
            return None
    
    # =========================================
    # 2. 공시 데이터 (DART API)
    # =========================================
    
    def collect_disclosure(self, stock_code, start_date, end_date):
        """공시 데이터 수집 (현재는 더미 데이터)"""
        # DART API 키 없으면 더미 반환
        date_range = pd.date_range(start_date, end_date, freq='D')
        df = pd.DataFrame({
            'Date': date_range,
            'disclosure_count': 0,
            'disclosure_impact': 0
        })
        return df.set_index('Date')
    
    # =========================================
    # 3. 뉴스 데이터 (네이버 뉴스)
    # =========================================
    
    def collect_news_sentiment(self, stock_name, date):
        """특정 날짜의 뉴스 감성 분석"""
        try:
            search_date = date.strftime('%Y.%m.%d')
            query = f"{stock_name}"
            
            url = "https://search.naver.com/search.naver"
            params = {
                'where': 'news',
                'query': query,
                'sort': 0,
                'ds': search_date,
                'de': search_date
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = soup.find_all('a', class_='news_tit')
            
            if not news_items:
                return {'news_count': 0, 'sentiment_score': 0}
            
            # 감성 분석 키워드
            positive = ['상승', '급등', '호재', '실적개선', '수주', '계약', '성장', '호조']
            negative = ['하락', '급락', '악재', '적자', '횡령', '배임', '감사의견', '한정', '부적정', '손실']
            
            sentiment = 0
            for item in news_items[:10]:
                title = item.text
                for kw in positive:
                    if kw in title:
                        sentiment += 1
                for kw in negative:
                    if kw in title:
                        sentiment -= 1
            
            return {
                'news_count': len(news_items[:10]),
                'sentiment_score': sentiment
            }
            
        except Exception as e:
            return {'news_count': 0, 'sentiment_score': 0}
    
    # =========================================
    # 4. 기존 데이터에 추가 병합
    # =========================================
    
    def update_stock_file(self, stock_code, stock_name):
        """기존 개별 파일에 추가 데이터 병합"""
        
        # 이미 완료했으면 스킵
        if stock_code in self.progress['completed']:
            print(f"   ✅ 이미 완료")
            return True
        
        file_path = self.data_dir / f"{stock_code}_{stock_name}.parquet"
        
        if not file_path.exists():
            print(f"   ❌ 파일 없음")
            return False
        
        try:
            df = pd.read_parquet(file_path)
            
            if 'Date' in df.columns:
                df = df.set_index('Date')
            elif df.index.name != 'Date':
                df.index.name = 'Date'
            
            start_date = df.index.min()
            end_date = df.index.max()
            
            # 1. 프로그램 매매
            print("   1️⃣ 프로그램 매매...", end=' ')
            df_program = self.collect_program_trading(stock_code, start_date, end_date)
            if df_program is not None and len(df_program) > 0:
                # 기존 컬럼 덮어쓰기
                for date, value in df_program['program_net'].items():
                    if date in df.index:
                        df.loc[date, 'program_net'] = value
                print(f"✅ {len(df_program)}일")
            else:
                print("⚠️ 데이터 없음")
            
            time.sleep(0.5)  # 크롤링 부하 방지
            
            # 2. 공시 (더미)
            print("   2️⃣ 공시 데이터...", end=' ')
            df_disclosure = self.collect_disclosure(stock_code, start_date, end_date)
            if df_disclosure is not None:
                for date in df_disclosure.index:
                    if date in df.index:
                        df.loc[date, 'disclosure_count'] = df_disclosure.loc[date, 'disclosure_count']
                        df.loc[date, 'disclosure_impact'] = df_disclosure.loc[date, 'disclosure_impact']
                print("✅ (더미)")
            else:
                print("⚠️ 실패")
            
            # 3. 뉴스 감성 (급락 날짜만 수집 - 시간 절약)
            print("   3️⃣ 뉴스 감성...", end=' ')
            
            # crash = 1인 날짜만 수집
            crash_dates = df[df['crash'] == 1].index
            
            if len(crash_dates) > 0:
                print(f"급락 {len(crash_dates)}일 수집 중...", end=' ')
                
                for crash_date in crash_dates:
                    news = self.collect_news_sentiment(stock_name, crash_date)
                    df.loc[crash_date, 'news_count'] = news['news_count']
                    df.loc[crash_date, 'sentiment_score'] = news['sentiment_score']
                    time.sleep(0.3)
                
                # 급락 아닌 날은 0
                df['news_count'] = df['news_count'].fillna(0)
                df['sentiment_score'] = df['sentiment_score'].fillna(0)
                print("✅")
            else:
                print("급락 없음 - 스킵")
            
            # 저장
            df.reset_index().to_parquet(file_path, index=False)
            
            # 진행상황 저장
            self.save_progress(stock_code)
            
            return True
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return False


def main():
    """전체 파일 업데이트"""
    collector = EnhancedDataCollector()
    
    # 개별 파일 목록
    data_dir = Path('./data/crash_rebound')
    files = list(data_dir.glob('*.parquet'))
    files = [f for f in files if f.name != 'all_stocks_3years.parquet']
    
    print(f"\n{'='*60}")
    print(f"📊 추가 데이터 수집 시작")
    print(f"총 {len(files)}개 파일")
    print(f"완료: {len(collector.progress['completed'])}개")
    print(f"남은: {len(files) - len(collector.progress['completed'])}개")
    print(f"{'='*60}\n")
    
    success = 0
    fail = 0
    
    for i, file_path in enumerate(files, 1):
        parts = file_path.stem.split('_')
        if len(parts) < 2:
            continue
        
        stock_code = parts[0]
        stock_name = '_'.join(parts[1:])
        
        print(f"[{i}/{len(files)}] {stock_name} ({stock_code})")
        
        if collector.update_stock_file(stock_code, stock_name):
            success += 1
        else:
            fail += 1
        
        # 진행률 출력
        if i % 100 == 0:
            print(f"\n{'='*60}")
            print(f"진행: {i}/{len(files)} ({i/len(files)*100:.1f}%)")
            print(f"성공: {success}, 실패: {fail}")
            print(f"{'='*60}\n")
    
    print(f"\n{'='*60}")
    print(f"🎉 추가 데이터 수집 완료!")
    print(f"성공: {success}, 실패: {fail}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
