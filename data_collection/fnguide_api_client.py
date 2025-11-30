"""
FnGuide DataGuide API 클라이언트
- 틱 데이터 수집
- VI 이벤트 조회
- 프로그램 매매 내역
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa


class FnGuideAPIClient:
    """FnGuide DataGuide API 래퍼"""
    
    def __init__(self, api_key, api_secret):
        """
        Args:
            api_key: FnGuide API 키
            api_secret: FnGuide API 시크릿
        
        발급 방법:
            1. https://www.fnguide.com 접속
            2. 1588-3003 전화
            3. DataGuide API 계약
            4. API 키 발급 (영업일 2~3일)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.fnguide.com/v1"  # 예시 URL
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'X-API-Secret': api_secret,
            'Content-Type': 'application/json'
        })
    
    def get_tick_data(self, stock_code, start_datetime, end_datetime):
        """
        틱 데이터 수집
        
        Args:
            stock_code: 종목코드 (예: '005930')
            start_datetime: 시작 시간 (datetime)
            end_datetime: 종료 시간 (datetime)
        
        Returns:
            DataFrame: 틱 데이터
              - timestamp: 체결 시간 (밀리초 단위)
              - price: 체결가
              - volume: 체결량
              - buy_sell: 매수(1)/매도(2)
        """
        endpoint = f"{self.base_url}/market/ticks"
        
        params = {
            'stock_code': stock_code,
            'start_datetime': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'end_datetime': end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'include_bid_ask': True  # 호가 포함
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data:
                print(f"[{stock_code}] 데이터 없음")
                return None
            
            # DataFrame 변환
            df = pd.DataFrame(data['data'])
            
            # 타임스탬프 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            print(f"[{stock_code}] {len(df):,}개 틱 수집 완료")
            return df
            
        except Exception as e:
            print(f"[{stock_code}] 틱 데이터 수집 오류: {e}")
            return None
    
    def get_vi_events(self, stock_code=None, start_date=None, end_date=None):
        """
        VI 이벤트 내역 조회
        
        Args:
            stock_code: 종목코드 (None이면 전체)
            start_date: 시작일 (datetime)
            end_date: 종료일 (datetime)
        
        Returns:
            DataFrame: VI 이벤트
              - vi_datetime: VI 발동 시간
              - stock_code: 종목코드
              - stock_name: 종목명
              - vi_type: 정적(static)/동적(dynamic)
              - trigger_price: 발동가
              - base_price: 기준가
              - reason: 발동 사유
              - release_datetime: 해제 시간
        """
        endpoint = f"{self.base_url}/market/vi_events"
        
        params = {
            'start_date': start_date.strftime('%Y-%m-%d') if start_date else None,
            'end_date': end_date.strftime('%Y-%m-%d') if end_date else None
        }
        
        if stock_code:
            params['stock_code'] = stock_code
        
        try:
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data['data'])
            
            print(f"✅ {len(df)}개 VI 이벤트 발견")
            return df
            
        except Exception as e:
            print(f"❌ VI 이벤트 조회 오류: {e}")
            return None
    
    def get_program_trading(self, stock_code, start_datetime, end_datetime):
        """
        프로그램 매매 내역 (초단위)
        
        Returns:
            DataFrame:
              - timestamp: 시간 (초단위)
              - program_buy: 프로그램 매수량
              - program_sell: 프로그램 매도량
              - program_net: 프로그램 순매수
        """
        endpoint = f"{self.base_url}/market/program_trading"
        
        params = {
            'stock_code': stock_code,
            'start_datetime': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'end_datetime': end_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data['data'])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['program_net'] = df['program_buy'] - df['program_sell']
            
            return df
            
        except Exception as e:
            print(f"프로그램 매매 조회 오류: {e}")
            return None
    
    def get_investor_trading(self, stock_code, start_datetime, end_datetime):
        """
        투자자별 매매 내역 (기관/외국인/개인)
        
        Returns:
            DataFrame:
              - timestamp
              - institution_buy/sell/net
              - foreign_buy/sell/net
              - individual_buy/sell/net
        """
        endpoint = f"{self.base_url}/market/investor_trading"
        
        params = {
            'stock_code': stock_code,
            'start_datetime': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'end_datetime': end_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data['data'])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            print(f"투자자별 매매 조회 오류: {e}")
            return None
    
    def collect_vi_event_data(self, vi_event, before_seconds=60, after_seconds=60):
        """
        VI 이벤트 전후 데이터 통합 수집
        
        Args:
            vi_event: VI 이벤트 정보 (dict)
            before_seconds: VI 발동 전 수집 시간 (초)
            after_seconds: VI 해제 후 수집 시간 (초)
        
        Returns:
            DataFrame: 통합 데이터 (틱 + 프로그램 + 투자자)
        """
        stock_code = vi_event['stock_code']
        vi_time = pd.to_datetime(vi_event['vi_datetime'])
        release_time = pd.to_datetime(vi_event['release_datetime'])
        
        # 수집 범위
        start_time = vi_time - timedelta(seconds=before_seconds)
        end_time = release_time + timedelta(seconds=after_seconds)
        
        print(f"\n{'='*60}")
        print(f"[{stock_code}] VI 이벤트 데이터 수집")
        print(f"VI 발동: {vi_time}")
        print(f"VI 해제: {release_time}")
        print(f"수집 범위: {start_time} ~ {end_time}")
        print(f"{'='*60}\n")
        
        # 1. 틱 데이터
        ticks = self.get_tick_data(stock_code, start_time, end_time)
        if ticks is None:
            return None
        
        time.sleep(0.5)  # API 부하 방지
        
        # 2. 프로그램 매매
        program = self.get_program_trading(stock_code, start_time, end_time)
        time.sleep(0.5)
        
        # 3. 투자자별 매매
        investor = self.get_investor_trading(stock_code, start_time, end_time)
        
        # 4. 데이터 병합 (timestamp 기준)
        df = ticks.copy()
        
        if program is not None:
            df = pd.merge_asof(
                df.sort_values('timestamp'),
                program[['timestamp', 'program_net']].sort_values('timestamp'),
                on='timestamp',
                direction='nearest'
            )
        
        if investor is not None:
            df = pd.merge_asof(
                df.sort_values('timestamp'),
                investor.sort_values('timestamp'),
                on='timestamp',
                direction='nearest'
            )
        
        # 5. VI 상태 레이블링
        df['vi_status'] = 0  # 정상
        df.loc[df['timestamp'] >= vi_time, 'vi_status'] = 1  # VI 발동
        df.loc[df['timestamp'] >= release_time, 'vi_status'] = 2  # VI 해제
        
        # 6. VI 메타데이터 추가
        df['vi_type'] = vi_event['vi_type']
        df['vi_reason'] = vi_event['reason']
        
        print(f"✅ 총 {len(df):,}개 데이터 포인트 수집 완료\n")
        
        return df
    
    def batch_collect_vi_events(self, start_date, end_date, output_dir='./data/vi_events'):
        """
        기간 내 모든 VI 이벤트 일괄 수집
        
        Args:
            start_date: 시작일
            end_date: 종료일
            output_dir: 저장 디렉토리
        
        Returns:
            int: 수집된 VI 이벤트 수
        """
        # VI 이벤트 목록 조회
        vi_events = self.get_vi_events(start_date=start_date, end_date=end_date)
        
        if vi_events is None or len(vi_events) == 0:
            print("❌ VI 이벤트 없음")
            return 0
        
        print(f"\n{'='*60}")
        print(f"총 {len(vi_events)}개 VI 이벤트 발견")
        print(f"{'='*60}\n")
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        
        for idx, vi_event in vi_events.iterrows():
            try:
                # VI 전후 데이터 수집
                df = self.collect_vi_event_data(vi_event)
                
                if df is not None and len(df) > 0:
                    # Parquet 저장 (압축 효율)
                    filename = (
                        f"{vi_event['stock_code']}_"
                        f"{pd.to_datetime(vi_event['vi_datetime']).strftime('%Y%m%d_%H%M%S')}.parquet"
                    )
                    filepath = f"{output_dir}/{filename}"
                    
                    df.to_parquet(filepath, compression='snappy')
                    print(f"💾 저장: {filepath}")
                    
                    success_count += 1
                
                # API 부하 방지
                time.sleep(1.0)
                
            except Exception as e:
                print(f"❌ {vi_event['stock_code']} 수집 실패: {e}")
                continue
        
        print(f"\n{'='*60}")
        print(f"✅ {success_count}/{len(vi_events)}개 VI 이벤트 수집 완료")
        print(f"{'='*60}\n")
        
        return success_count


def main():
    """사용 예제"""
    
    # ============================================
    # FnGuide API 키 설정
    # ============================================
    # 실제 발급받은 키로 교체
    API_KEY = "발급받은_API_KEY"
    API_SECRET = "발급받은_API_SECRET"
    
    client = FnGuideAPIClient(API_KEY, API_SECRET)
    
    # ============================================
    # 예제 1: 특정 VI 이벤트 수집
    # ============================================
    vi_event_example = {
        'stock_code': '005930',
        'vi_datetime': '2024-11-15 09:05:23',
        'release_datetime': '2024-11-15 09:07:45',
        'vi_type': 'dynamic',
        'reason': '급락'
    }
    
    df = client.collect_vi_event_data(vi_event_example)
    if df is not None:
        print(df.head())
    
    # ============================================
    # 예제 2: 기간 내 전체 VI 이벤트 수집
    # ============================================
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    
    count = client.batch_collect_vi_events(
        start_date=start,
        end_date=end,
        output_dir='./data/vi_events/2024'
    )
    
    print(f"\n🎉 2024년 {count}개 VI 이벤트 수집 완료!")


if __name__ == '__main__':
    main()
