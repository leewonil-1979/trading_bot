"""
통합 실시간 데이터 수집기
- KIS WebSocket (틱 + 호가)
- 네이버 크롤링 (프로그램 매매 10분)
- DART API (공시 실시간)
- 뉴스 크롤링
"""
import asyncio
try:
    import websocket
except ImportError:
    websocket = None  # type: ignore
import json
import requests
import pandas as pd
from datetime import datetime, time as dt_time
from pathlib import Path
import threading
import time
from bs4 import BeautifulSoup
import pyarrow.parquet as pq
import pyarrow as pa
from typing import Optional, Dict, List, Any


class RealtimeDataCollector:
    """실시간 통합 데이터 수집기"""
    
    def __init__(self, kis_key, kis_secret, dart_key):
        """
        Args:
            kis_key: 한국투자증권 APP KEY
            kis_secret: 한국투자증권 APP SECRET
            dart_key: DART API 키
        """
        self.kis_key = kis_key
        self.kis_secret = kis_secret
        self.dart_key = dart_key
        
        # 데이터 버퍼
        self.tick_buffer = {}  # {stock_code: [tick_data]}
        self.orderbook_buffer = {}  # {stock_code: [orderbook_data]}
        self.program_trading = {}  # {stock_code: program_data}
        self.news_buffer = []
        self.disclosure_buffer = []
        
        # VI 이벤트 감지
        self.vi_events = []
        self.last_prices = {}  # VI 감지용
        
        # 실행 상태
        self.is_running = False
        self.market_open = dt_time(9, 0)
        self.market_close = dt_time(15, 30)
    
    # ============================================
    # 1. KIS WebSocket - 틱 데이터
    # ============================================
    
    def start_kis_websocket(self, stock_codes):
        """
        KIS WebSocket 시작
        
        Args:
            stock_codes: 구독할 종목 리스트
        """
        ws_url = "ws://ops.koreainvestment.com:21000"
        
        def on_message(ws, message):
            """틱 데이터 수신"""
            try:
                data = message.split('|')
                if len(data) < 4:
                    return
                
                header = data[0]
                body = data[3]
                
                # 종목코드 추출
                stock_code = header[24:30]
                
                # 틱 데이터 파싱
                tick = {
                    'timestamp': datetime.now(),
                    'stock_code': stock_code,
                    'price': int(body[0:10]),
                    'volume': int(body[10:20]),
                    'buy_sell': body[20]  # 1=매수, 2=매도
                }
                
                # 버퍼에 저장
                if stock_code not in self.tick_buffer:
                    self.tick_buffer[stock_code] = []
                self.tick_buffer[stock_code].append(tick)
                
                # VI 감지
                self.detect_vi(stock_code, tick['price'])
                
                # 1분마다 저장
                if datetime.now().second == 0:
                    self.save_tick_buffer()
                
            except Exception as e:
                print(f"틱 데이터 파싱 오류: {e}")
        
        def on_open(ws):
            """WebSocket 연결"""
            print("✅ KIS WebSocket 연결 성공")
            
            # 토큰 발급
            token = self.get_kis_token()
            
            # 종목 구독
            for stock_code in stock_codes:
                subscribe_msg = {
                    "header": {
                        "approval_key": token,
                        "custtype": "P",
                        "tr_type": "1",
                        "content-type": "utf-8"
                    },
                    "body": {
                        "input": {
                            "tr_id": "H0STCNT0",  # 실시간 체결
                            "tr_key": stock_code
                        }
                    }
                }
                ws.send(json.dumps(subscribe_msg))
                print(f"📡 {stock_code} 구독 시작")
        
        # WebSocket 실행
        ws = websocket.WebSocketApp(  # type: ignore
            ws_url,
            on_open=on_open,
            on_message=on_message
        )
        
        ws.run_forever()
    
    # ============================================
    # 2. 네이버 크롤링 - 프로그램 매매
    # ============================================
    
    def collect_program_trading(self, stock_codes):
        """
        10분마다 프로그램 매매 크롤링
        
        Args:
            stock_codes: 종목 리스트
        """
        while self.is_running:
            for stock_code in stock_codes:
                try:
                    url = f"https://finance.naver.com/item/frgn.naver?code={stock_code}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 프로그램 매매 테이블 파싱
                    table = soup.select_one('table.type2')
                    if table:
                        rows = table.select('tr')
                        if len(rows) > 1:
                            cols = rows[1].select('td')
                            if len(cols) >= 7:
                                program_data = {
                                    'timestamp': datetime.now(),
                                    'stock_code': stock_code,
                                    'program_buy': int(cols[1].text.replace(',', '') or 0),
                                    'program_sell': int(cols[2].text.replace(',', '') or 0),
                                    'institution_buy': int(cols[3].text.replace(',', '') or 0),
                                    'institution_sell': int(cols[4].text.replace(',', '') or 0),
                                    'foreign_buy': int(cols[5].text.replace(',', '') or 0),
                                    'foreign_sell': int(cols[6].text.replace(',', '') or 0)
                                }
                                
                                self.program_trading[stock_code] = program_data
                                print(f"📊 [{stock_code}] 프로그램 매매 업데이트")
                    
                    time.sleep(1)  # 크롤링 간격
                    
                except Exception as e:
                    print(f"프로그램 매매 크롤링 오류 [{stock_code}]: {e}")
            
            # 10분 대기
            print("⏰ 프로그램 매매 10분 대기...")
            time.sleep(600)
    
    # ============================================
    # 3. DART API - 공시
    # ============================================
    
    def collect_disclosures(self, stock_codes):
        """
        5분마다 공시 수집
        
        Args:
            stock_codes: 종목 리스트 (종목코드 → 기업코드 변환 필요)
        """
        while self.is_running:
            try:
                url = "https://opendart.fss.or.kr/api/list.json"
                params = {
                    'crtfc_key': self.dart_key,
                    'bgn_de': datetime.now().strftime('%Y%m%d'),
                    'end_de': datetime.now().strftime('%Y%m%d'),
                    'page_count': 100
                }
                
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data['status'] == '000':
                    disclosures = data.get('list', [])
                    
                    for disclosure in disclosures:
                        self.disclosure_buffer.append({
                            'timestamp': datetime.now(),
                            'corp_code': disclosure['corp_code'],
                            'corp_name': disclosure['corp_name'],
                            'report_nm': disclosure['report_nm'],
                            'rcept_dt': disclosure['rcept_dt'],
                            'flr_nm': disclosure['flr_nm']
                        })
                    
                    print(f"📢 공시 {len(disclosures)}건 수집")
                
            except Exception as e:
                print(f"공시 수집 오류: {e}")
            
            # 5분 대기
            time.sleep(300)
    
    # ============================================
    # 4. 뉴스 크롤링
    # ============================================
    
    def collect_news(self, stock_codes):
        """
        5분마다 뉴스 크롤링
        
        Args:
            stock_codes: 종목 리스트
        """
        while self.is_running:
            for stock_code in stock_codes:
                try:
                    url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1"
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    news_items = soup.select('table.type5 tr')
                    
                    for item in news_items[:5]:  # 최근 5개만
                        link = item.select_one('a.tit')
                        if link:
                            news = {
                                'timestamp': datetime.now(),
                                'stock_code': stock_code,
                                'title': link.text.strip(),
                                'url': 'https://finance.naver.com' + str(link.get('href', '')),  # type: ignore
                                'sentiment': self.analyze_sentiment(link.text)
                            }
                            self.news_buffer.append(news)
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"뉴스 크롤링 오류 [{stock_code}]: {e}")
            
            print(f"📰 뉴스 {len(self.news_buffer)}건 수집")
            
            # 5분 대기
            time.sleep(300)
    
    # ============================================
    # 5. VI 감지 알고리즘
    # ============================================
    
    def detect_vi(self, stock_code, current_price):
        """
        VI 발생 감지 (급등/급락)
        
        Args:
            stock_code: 종목코드
            current_price: 현재가
        """
        if stock_code not in self.last_prices:
            self.last_prices[stock_code] = current_price
            return
        
        last_price = self.last_prices[stock_code]
        change_rate = (current_price - last_price) / last_price
        
        # VI 발동 기준 (±8%)
        if abs(change_rate) > 0.08:
            vi_event = {
                'timestamp': datetime.now(),
                'stock_code': stock_code,
                'vi_type': 'up' if change_rate > 0 else 'down',
                'trigger_price': current_price,
                'base_price': last_price,
                'change_rate': change_rate
            }
            
            self.vi_events.append(vi_event)
            print(f"🚨 VI 감지! [{stock_code}] {change_rate:.2%}")
            
            # VI 전후 60초 데이터 별도 저장
            self.save_vi_event(vi_event)
        
        self.last_prices[stock_code] = current_price
    
    # ============================================
    # 6. 데이터 저장
    # ============================================
    
    def save_tick_buffer(self):
        """1분 단위 틱 데이터 저장"""
        now = datetime.now()
        
        for stock_code, ticks in self.tick_buffer.items():
            if len(ticks) == 0:
                continue
            
            # Parquet 저장
            df = pd.DataFrame(ticks)
            
            output_dir = f"./data/realtime/{now.year}/{now.month:02d}/{now.day:02d}"
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            filename = f"{stock_code}_{now.hour:02d}{now.minute:02d}_ticks.parquet"
            filepath = f"{output_dir}/{filename}"
            
            df.to_parquet(filepath, compression='snappy')
            print(f"💾 [{stock_code}] {len(ticks)}개 틱 저장 → {filepath}")
        
        # 버퍼 초기화
        self.tick_buffer = {}
    
    def save_vi_event(self, vi_event):
        """VI 이벤트 별도 저장"""
        stock_code = vi_event['stock_code']
        timestamp = vi_event['timestamp']
        
        # VI 전후 60초 틱 데이터 수집
        # (실제로는 버퍼에서 추출)
        
        output_dir = f"./data/vi_events/{timestamp.year}/{timestamp.month:02d}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = f"{stock_code}_{timestamp.strftime('%Y%m%d_%H%M%S')}_vi.json"
        filepath = f"{output_dir}/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(vi_event, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"🚨 VI 이벤트 저장 → {filepath}")
    
    # ============================================
    # 7. 유틸리티
    # ============================================
    
    def get_kis_token(self):
        """KIS 접근 토큰 발급"""
        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.kis_key,
            "appsecret": self.kis_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise Exception(f"토큰 발급 실패: {response.text}")
    
    def analyze_sentiment(self, text):
        """뉴스 감성 분석 (간단 버전)"""
        positive = ['상승', '급등', '호재', '성장', '최고', '돌파']
        negative = ['하락', '급락', '악재', '손실', '최저', '부진']
        
        pos_count = sum(1 for word in positive if word in text)
        neg_count = sum(1 for word in negative if word in text)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    def is_market_time(self):
        """장 시간 확인"""
        now = datetime.now().time()
        return self.market_open <= now <= self.market_close
    
    # ============================================
    # 8. 메인 실행
    # ============================================
    
    def start(self, stock_codes):
        """
        실시간 수집 시작
        
        Args:
            stock_codes: 구독할 종목 리스트
        """
        print("\n" + "="*60)
        print("🚀 실시간 데이터 수집 시작")
        print(f"종목: {len(stock_codes)}개")
        print(f"시작 시간: {datetime.now()}")
        print("="*60 + "\n")
        
        self.is_running = True
        
        # 1. KIS WebSocket (별도 스레드)
        ws_thread = threading.Thread(
            target=self.start_kis_websocket,
            args=(stock_codes,)
        )
        ws_thread.daemon = True
        ws_thread.start()
        
        # 2. 프로그램 매매 크롤링
        program_thread = threading.Thread(
            target=self.collect_program_trading,
            args=(stock_codes,)
        )
        program_thread.daemon = True
        program_thread.start()
        
        # 3. 공시 수집
        disclosure_thread = threading.Thread(
            target=self.collect_disclosures,
            args=(stock_codes,)
        )
        disclosure_thread.daemon = True
        disclosure_thread.start()
        
        # 4. 뉴스 수집
        news_thread = threading.Thread(
            target=self.collect_news,
            args=(stock_codes,)
        )
        news_thread.daemon = True
        news_thread.start()
        
        print("✅ 모든 수집기 가동 중...")
        
        # 메인 루프 (장 시간 확인)
        try:
            while True:
                if not self.is_market_time():
                    print(f"\n⏰ 장 마감 ({datetime.now().time()})")
                    print("내일 09:00에 재시작합니다.")
                    break
                
                time.sleep(60)  # 1분마다 체크
                
        except KeyboardInterrupt:
            print("\n\n사용자 중단")
        finally:
            self.stop()
    
    def stop(self):
        """수집 중지"""
        self.is_running = False
        
        # 버퍼 저장
        self.save_tick_buffer()
        
        print("\n" + "="*60)
        print("🛑 실시간 수집 종료")
        print(f"수집 VI 이벤트: {len(self.vi_events)}개")
        print(f"종료 시간: {datetime.now()}")
        print("="*60)


def main():
    """실행 예제"""
    
    # ============================================
    # API 키 설정
    # ============================================
    KIS_KEY = "PSSTDXlBU05I5MWOWk9tzEcsPNdqQ8HejPax"
    KIS_SECRET = "aOMY7LAayo5v0/BU+3SdMF03bmhu7pEqI7yrZK0N5CxblbVNchK+Y8Q4rt8qbhTe8HpoFwzPiOvCLfJAJSVfeLgo7qC3mTacLix9XmwfbYbqYWFihBJYMuHhjpEH4tOZvq77ozfGkpRGrwJzm7/UaXWR6Z/PXKYSWLToRN+5cCt6u1sNdv4="
    DART_KEY = "발급받은_DART_API_KEY"  # https://opendart.fss.or.kr
    
    # ============================================
    # 수집 대상 종목 (VI 발생 종목 위주)
    # ============================================
    # vi_stocks.json에서 로드
    import json
    with open('./data/raw/vi_stocks.json', 'r', encoding='utf-8') as f:
        vi_data = json.load(f)
    
    # 상위 50개 종목
    stock_codes = [s['stock_code'] for s in vi_data['stocks'][:50]]
    
    print(f"✅ 수집 종목: {len(stock_codes)}개")
    print(f"예시: {stock_codes[:5]}")
    
    # ============================================
    # 실시간 수집 시작
    # ============================================
    collector = RealtimeDataCollector(KIS_KEY, KIS_SECRET, DART_KEY)
    collector.start(stock_codes)


if __name__ == '__main__':
    main()
