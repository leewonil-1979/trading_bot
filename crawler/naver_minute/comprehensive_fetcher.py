"""
네이버 금융 종합 데이터 수집 모듈
VI 학습에 필요한 모든 데이터 수집:
1. 분봉 (OHLCV)
2. 프로그램 매매 (기관/외국인/개인)
3. 뉴스/공시
4. VI 발생 내역
"""
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import json
from pathlib import Path


class ComprehensiveDataFetcher:
    """VI 학습용 종합 데이터 수집기"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.naver.com/'
        }
    
    # ============= 1. 분봉 데이터 (OHLCV) =============
    
    def fetch_minute_candles(self, stock_code, date, timeframe='1'):
        """
        특정 날짜의 분봉 데이터 수집
        
        Args:
            stock_code: 종목코드
            date: 날짜 (YYYYMMDD)
            timeframe: '1' (1분) or '3' (3분)
        
        Returns:
            DataFrame: timestamp, open, high, low, close, volume
        """
        url = f"https://api.finance.naver.com/siseJson.naver"
        params = {
            'symbol': stock_code,
            'requestType': timeframe,
            'startTime': date + '000000',
            'endTime': date + '235959',
            'timeframe': 'day',
            'count': 900
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            
            if not data or len(data) < 2:
                return None
            
            df = pd.DataFrame(data[1:], columns=data[0])
            df = df.rename(columns={
                '체결시간': 'timestamp',
                '시가': 'open', '고가': 'high', '저가': 'low', 
                '종가': 'close', '거래량': 'volume'
            })
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y%m%d%H%M%S')
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            df['volume'] = df['volume'].astype(int)
            
            return df
            
        except Exception as e:
            print(f"[{stock_code}] 분봉 수집 오류: {e}")
            return None
    
    # ============= 2. 프로그램 매매 데이터 =============
    
    def fetch_program_trading(self, stock_code, date):
        """
        투자자별 매매 동향 (기관/외국인/개인)
        
        Returns:
            dict: {
                'institutional_buy': 기관 매수량,
                'institutional_sell': 기관 매도량,
                'foreign_buy': 외국인 매수량,
                'foreign_sell': 외국인 매도량,
                'individual_buy': 개인 매수량,
                'individual_sell': 개인 매도량
            }
        """
        url = f"https://finance.naver.com/item/frgn.naver?code={stock_code}"
        
        try:
            resp = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 테이블에서 투자자별 데이터 추출
            table = soup.select_one('table.type2')
            if not table:
                return None
            
            rows = table.select('tr')
            data = {
                'date': date,
                'institutional_buy': 0,
                'institutional_sell': 0,
                'foreign_buy': 0,
                'foreign_sell': 0,
                'individual_buy': 0,
                'individual_sell': 0
            }
            
            for row in rows:
                cols = row.select('td')
                if len(cols) >= 7:
                    row_date = cols[0].text.strip().replace('.', '')
                    if row_date == date:
                        data['foreign_buy'] = int(cols[1].text.replace(',', '') or 0)
                        data['foreign_sell'] = int(cols[2].text.replace(',', '') or 0)
                        data['institutional_buy'] = int(cols[3].text.replace(',', '') or 0)
                        data['institutional_sell'] = int(cols[4].text.replace(',', '') or 0)
                        break
            
            return data
            
        except Exception as e:
            print(f"[{stock_code}] 프로그램 매매 수집 오류: {e}")
            return None
    
    # ============= 3. 뉴스 데이터 =============
    
    def fetch_news(self, stock_code, date):
        """
        종목 관련 뉴스 수집
        
        Returns:
            list: [{'time': '', 'title': '', 'url': '', 'sentiment': ''}]
        """
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1"
        
        try:
            resp = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            news_list = []
            news_items = soup.select('table.type5 tr')
            
            for item in news_items:
                link = item.select_one('a.tit')
                if not link:
                    continue
                
                title = link.text.strip()
                news_url = 'https://finance.naver.com' + str(link.get('href', ''))  # type: ignore
                
                date_elem = item.select_one('td.date')
                news_date = date_elem.text.strip() if date_elem else ''
                
                # 감성 분석 (간단한 키워드 기반)
                sentiment = self._analyze_sentiment(title)
                
                news_list.append({
                    'date': news_date,
                    'title': title,
                    'url': news_url,
                    'sentiment': sentiment
                })
            
            return news_list
            
        except Exception as e:
            print(f"[{stock_code}] 뉴스 수집 오류: {e}")
            return []
    
    def _analyze_sentiment(self, text):
        """뉴스 제목 감성 분석"""
        positive_words = ['상승', '급등', '호재', '성장', '증가', '개선', '최고', '신고가']
        negative_words = ['하락', '급락', '악재', '감소', '부진', '최저', '적자', '손실']
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    # ============= 4. 공시 정보 =============
    
    def fetch_disclosures(self, stock_code, start_date, end_date):
        """
        공시 정보 수집 (DART API 또는 네이버)
        
        Returns:
            list: [{'date': '', 'title': '', 'type': ''}]
        """
        url = f"https://finance.naver.com/item/news_notice.naver?code={stock_code}"
        
        try:
            resp = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            disclosures = []
            items = soup.select('table.type5 tr')
            
            for item in items:
                link = item.select_one('a.tit')
                if not link:
                    continue
                
                title = link.text.strip()
                date_elem = item.select_one('td.date')
                disc_date = date_elem.text.strip() if date_elem else ''
                
                disclosures.append({
                    'date': disc_date,
                    'title': title,
                    'type': self._classify_disclosure(title)
                })
            
            return disclosures
            
        except Exception as e:
            print(f"[{stock_code}] 공시 수집 오류: {e}")
            return []
    
    def _classify_disclosure(self, title):
        """공시 유형 분류"""
        if '실적' in title or '영업' in title:
            return 'earnings'
        elif '유상증자' in title or '증자' in title:
            return 'capital_increase'
        elif '배당' in title:
            return 'dividend'
        elif '합병' in title or '인수' in title:
            return 'ma'
        else:
            return 'other'
    
    # ============= 5. VI 발생 내역 =============
    
    def fetch_vi_history(self, stock_code, date):
        """
        VI 발생 내역 조회
        
        Returns:
            list: [{'time': '', 'type': 'static/dynamic', 'price': '', 'reason': ''}]
        """
        # KRX 정보데이터시스템에서 VI 내역 조회
        # 또는 네이버 차트에서 추출
        url = f"http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        
        # 실제 구현은 KRX API 필요
        # 여기서는 분봉 데이터에서 VI 추정
        return []
    
    # ============= 통합 수집 =============
    
    def collect_all_data(self, stock_code, stock_name, date):
        """
        특정 날짜의 모든 데이터 수집
        
        Returns:
            dict: {
                'candles': DataFrame,
                'program_trading': dict,
                'news': list,
                'disclosures': list,
                'vi_events': list
            }
        """
        print(f"[{stock_code} {stock_name}] {date} 종합 데이터 수집 중...")
        
        data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'date': date,
            'candles': None,
            'program_trading': None,
            'news': [],
            'disclosures': [],
            'vi_events': []
        }
        
        # 1. 분봉
        data['candles'] = self.fetch_minute_candles(stock_code, date)
        time.sleep(0.3)
        
        # 2. 프로그램 매매
        data['program_trading'] = self.fetch_program_trading(stock_code, date)
        time.sleep(0.3)
        
        # 3. 뉴스
        data['news'] = self.fetch_news(stock_code, date)
        time.sleep(0.3)
        
        # 4. 공시
        data['disclosures'] = self.fetch_disclosures(stock_code, date, date)
        time.sleep(0.3)
        
        # 5. VI 내역
        data['vi_events'] = self.fetch_vi_history(stock_code, date)
        
        return data
    
    def save_comprehensive_data(self, data, output_dir='./data/comprehensive'):
        """통합 데이터 저장"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        stock_code = data['stock_code']
        date = data['date']
        
        # JSON으로 저장
        filepath = f"{output_dir}/{stock_code}_{date}.json"
        
        # DataFrame은 JSON 직렬화를 위해 변환
        save_data = data.copy()
        if data['candles'] is not None:
            save_data['candles'] = data['candles'].to_dict('records')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"저장 완료: {filepath}")


def main():
    """테스트"""
    fetcher = ComprehensiveDataFetcher()
    
    # 삼성전자 오늘 데이터 수집
    today = datetime.now().strftime('%Y%m%d')
    data = fetcher.collect_all_data('005930', '삼성전자', today)
    
    print("\n=== 수집 결과 ===")
    print(f"분봉: {len(data['candles']) if data['candles'] is not None else 0}개")
    print(f"프로그램 매매: {data['program_trading']}")
    print(f"뉴스: {len(data['news'])}개")
    print(f"공시: {len(data['disclosures'])}개")
    
    fetcher.save_comprehensive_data(data)


if __name__ == '__main__':
    main()
