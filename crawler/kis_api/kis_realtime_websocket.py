"""
KIS API 웹소켓 실시간 체결 데이터 수집
- 실시간 틱/분봉 스트리밍
- VI 발생 즉시 감지 가능
"""
try:
    import websocket
except ImportError:
    websocket = None  # type: ignore
import json
import requests
from datetime import datetime
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable


class KISRealtimeCollector:
    """KIS API 실시간 데이터 수집기"""
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.ws_url = "ws://ops.koreainvestment.com:21000"
        self.access_token: Optional[str] = None
        self.approval_key: Optional[str] = None
        
    def get_access_token(self) -> bool:
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            print("✅ 토큰 발급 성공")
            return True
        else:
            print(f"❌ 토큰 발급 실패: {response.text}")
            return False
    
    def get_approval_key(self):
        """웹소켓 접속키 발급"""
        url = f"{self.base_url}/oauth2/Approval"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            self.approval_key = response.json()['approval_key']
            print("✅ 웹소켓 접속키 발급 성공")
            return True
        else:
            print(f"❌ 접속키 발급 실패: {response.text}")
            return False
    
    def subscribe_realtime(self, stock_codes, callback_func=None):
        """
        실시간 체결 데이터 구독
        
        Args:
            stock_codes: 종목코드 리스트 ['005930', '000660', ...]
            callback_func: 데이터 수신 콜백 함수
        """
        if not self.access_token:
            self.get_access_token()
        if not self.approval_key:
            self.get_approval_key()
        
        def on_message(ws, message):
            """메시지 수신 핸들러"""
            try:
                data = message.split('|')
                if len(data) < 4:
                    return
                
                # 실시간 체결가 파싱
                header = data[0]
                body = data[3]
                
                # 체결 데이터 추출
                tick_data = {
                    'timestamp': datetime.now(),
                    'stock_code': header[24:30],  # 종목코드
                    'price': int(body[0:10]),      # 체결가
                    'volume': int(body[10:20]),    # 거래량
                    'buy_sell': body[20]           # 매수(1)/매도(2)
                }
                
                if callback_func:
                    callback_func(tick_data)
                else:
                    print(f"[{tick_data['timestamp'].strftime('%H:%M:%S')}] "
                          f"{tick_data['stock_code']}: {tick_data['price']:,}원 "
                          f"({tick_data['volume']:,}주)")
                    
            except Exception as e:
                print(f"메시지 파싱 오류: {e}")
        
        def on_open(ws):
            """연결 성공"""
            print("✅ 웹소켓 연결 성공")
            
            # 실시간 체결가 구독 메시지 전송
            for stock_code in stock_codes:
                subscribe_data = {
                    "header": {
                        "approval_key": self.approval_key,
                        "custtype": "P",
                        "tr_type": "1",
                        "content-type": "utf-8"
                    },
                    "body": {
                        "input": {
                            "tr_id": "H0STCNT0",  # 실시간 체결가
                            "tr_key": stock_code
                        }
                    }
                }
                ws.send(json.dumps(subscribe_data))
                print(f"📡 {stock_code} 구독 시작")
        
        def on_error(ws, error):
            print(f"❌ 웹소켓 오류: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print(f"🔌 웹소켓 연결 종료: {close_msg}")
        
        # 웹소켓 연결
        ws = websocket.WebSocketApp(  # type: ignore
            self.ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        print("\n🚀 실시간 스트리밍 시작...")
        ws.run_forever()
    
    def collect_1min_candles(self, stock_codes, duration_minutes=60):
        """
        실시간 체결을 1분봉으로 집계
        
        Args:
            stock_codes: 종목코드 리스트
            duration_minutes: 수집 시간 (분)
        """
        candles = {code: [] for code in stock_codes}
        current_candle = {code: None for code in stock_codes}
        
        def save_tick(tick):
            """틱 데이터 → 1분봉 변환"""
            code = tick['stock_code']
            minute = tick['timestamp'].replace(second=0, microsecond=0)
            
            # 새 분봉 시작
            if current_candle[code] is None or current_candle[code]['timestamp'] != minute:  # type: ignore
                # 이전 분봉 저장
                if current_candle[code]:
                    candles[code].append(current_candle[code])
                
                # 새 분봉 초기화
                current_candle[code] = {  # type: ignore
                    'timestamp': minute,
                    'open': tick['price'],
                    'high': tick['price'],
                    'low': tick['price'],
                    'close': tick['price'],
                    'volume': tick['volume']
                }
            else:
                # 기존 분봉 업데이트
                candle = current_candle[code]
                if candle is not None:
                    candle['high'] = max(candle['high'], tick['price'])
                    candle['low'] = min(candle['low'], tick['price'])
                    candle['close'] = tick['price']
                    candle['volume'] = candle['volume'] + tick['volume']
        
        # 실시간 수집 시작
        import threading
        import time
        
        # 종료 타이머
        def stop_after_duration():
            time.sleep(duration_minutes * 60)
            print(f"\n⏰ {duration_minutes}분 수집 완료")
            
            # 결과 저장
            for code in stock_codes:
                if len(candles[code]) > 0:
                    df = pd.DataFrame(candles[code])
                    output_file = f"./data/realtime/{code}_1min_{datetime.now().strftime('%Y%m%d')}.csv"
                    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    print(f"💾 {code}: {len(df)}개 분봉 저장 → {output_file}")
        
        timer = threading.Thread(target=stop_after_duration)
        timer.daemon = True
        timer.start()
        
        # 스트리밍 시작
        self.subscribe_realtime(stock_codes, callback_func=save_tick)


def main():
    """사용 예제"""
    APP_KEY = "PSSTDXlBU05I5MWOWk9tzEcsPNdqQ8HejPax"
    APP_SECRET = "aOMY7LAayo5v0/BU+3SdMF03bmhu7pEqI7yrZK0N5CxblbVNchK+Y8Q4rt8qbhTe8HpoFwzPiOvCLfJAJSVfeLgo7qC3mTacLix9XmwfbYbqYWFihBJYMuHhjpEH4tOZvq77ozfGkpRGrwJzm7/UaXWR6Z/PXKYSWLToRN+5cCt6u1sNdv4="
    
    collector = KISRealtimeCollector(APP_KEY, APP_SECRET)
    
    # 삼성전자, SK하이닉스 실시간 체결 수집 (60분)
    target_stocks = ['005930', '000660']
    
    print("\n" + "="*60)
    print("실시간 분봉 수집 시작")
    print(f"종목: {target_stocks}")
    print(f"시간: 60분")
    print("="*60 + "\n")
    
    collector.collect_1min_candles(target_stocks, duration_minutes=60)


if __name__ == '__main__':
    main()
