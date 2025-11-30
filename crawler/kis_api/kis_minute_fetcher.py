"""
한국투자증권 KIS API를 사용한 실제 분봉 데이터 수집
- 1분봉 제공 ✅
- 무료 (계좌 개설 필요)
- API 키 발급: https://apiportal.koreainvestment.com
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time


class KISMinuteFetcher:
    """한국투자증권 API 분봉 수집"""
    
    def __init__(self, app_key, app_secret):
        self.app_key = "PSSTDXlBU05I5MWOWk9tzEcsPNdqQ8HejPax"
        self.app_secret = "aOMY7LAayo5v0/BU+3SdMF03bmhu7pEqI7yrZK0N5CxblbVNchK+Y8Q4rt8qbhTe8HpoFwzPiOvCLfJAJSVfeLgo7qC3mTacLix9XmwfbYbqYWFihBJYMuHhjpEH4tOZvq77ozfGkpRGrwJzm7/UaXWR6Z/PXKYSWLToRN+5cCt6u1sNdv4="
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.access_token = None
        
    def get_access_token(self):
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
            print("토큰 발급 성공")
        else:
            raise Exception(f"토큰 발급 실패: {response.text}")
    
    def fetch_minute_data(self, stock_code, start_date, end_date):
        """
        1분봉 데이터 수집
        
        Args:
            stock_code: 종목코드 (6자리)
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
        
        Returns:
            DataFrame: timestamp, open, high, low, close, volume
        """
        if not self.access_token:
            self.get_access_token()
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST03010100"  # 국내주식 시간별 체결가
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 주식
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_HOUR_1": start_date,  # 조회 시작 일자
            "FID_PW_DATA_INCU_YN": "N"
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"API 오류: {response.status_code}")
            print(f"응답: {response.text}")
            return None
        
        data = response.json()
        
        print(f"API 응답 키: {data.keys()}")
        if 'msg1' in data:
            print(f"메시지: {data['msg1']}")
        
        if 'output2' not in data:
            print(f"전체 응답: {data}")
            return None
        
        # 데이터프레임 변환
        df = pd.DataFrame(data['output2'])
        
        # 컬럼명 변경
        df = df.rename(columns={
            'stck_bsop_date': 'date',
            'stck_cntg_hour': 'time',
            'stck_prpr': 'close',
            'stck_oprc': 'open',
            'stck_hgpr': 'high',
            'stck_lwpr': 'low',
            'cntg_vol': 'volume'
        })
        
        # timestamp 생성
        df['timestamp'] = pd.to_datetime(df['date'] + df['time'], format='%Y%m%d%H%M%S')
        
        # 필요한 컬럼만 선택
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # 데이터 타입 변환
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        df['volume'] = df['volume'].astype(int)
        
        return df.sort_values('timestamp').reset_index(drop=True)  # type: ignore
    
    def fetch_historical_minutes(self, stock_code, stock_name, days_back=730):
        """
        과거 분봉 데이터 수집 (여러 번 호출)
        
        KIS API는 한 번에 최대 30일치만 제공
        → 2년치는 24번 호출 필요
        """
        print(f"[{stock_code} {stock_name}] 분봉 데이터 수집 시작...")
        
        all_data = []
        end_date = datetime.now()
        
        # 30일씩 쪼개서 수집
        for i in range(0, days_back, 30):
            start = end_date - timedelta(days=min(i+30, days_back))
            end = end_date - timedelta(days=i)
            
            df = self.fetch_minute_data(
                stock_code,
                start.strftime('%Y%m%d'),
                end.strftime('%Y%m%d')
            )
            
            if df is not None and len(df) > 0:
                all_data.append(df)
                print(f"  {start.date()} ~ {end.date()}: {len(df)}개 분봉")
            
            time.sleep(0.2)  # API 부하 방지
        
        if not all_data:
            return None
        
        result = pd.concat(all_data, ignore_index=True)
        result = result.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        print(f"[{stock_code}] 총 {len(result)}개 분봉 수집 완료\n")
        return result


def main():
    """사용 예제"""
    # ============================================
    # 1. API 키 발급 방법
    # ============================================
    # 1) https://apiportal.koreainvestment.com 접속
    # 2) 회원가입 (한투 계좌 필요)
    # 3) [서비스 신청] → [국내주식] 선택
    # 4) 앱 등록 → APP KEY, APP SECRET 복사
    # 5) 아래에 붙여넣기
    
    APP_KEY = "발급받은_APP_KEY를_여기에"
    APP_SECRET = "발급받은_APP_SECRET을_여기에"
    
    # ============================================
    # 2. 사용 예제
    # ============================================
    fetcher = KISMinuteFetcher(APP_KEY, APP_SECRET)
    
    # 삼성전자 1분봉 수집 (최근 30일)
    df = fetcher.fetch_historical_minutes('005930', '삼성전자', days_back=30)
    
    if df is not None:
        print("\n=== 수집 결과 ===")
        print(df.head(20))
        print(f"\n총 {len(df)}개 분봉")
        print(f"기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        
        # CSV 저장
        df.to_csv('005930_minutes.csv', index=False, encoding='utf-8-sig')
        print("\n저장 완료: 005930_minutes.csv")
    else:
        print("데이터 수집 실패 - API 키를 확인하세요")


if __name__ == '__main__':
    main()
