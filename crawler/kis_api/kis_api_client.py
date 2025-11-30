"""
한국투자증권 KIS API 클라이언트
실제 주문 실행을 위한 모듈
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional
import json
import requests
import yaml
from datetime import datetime
try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None  # type: ignore


class KISApiClient:
    """한국투자증권 OpenAPI 클라이언트"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로
        """
        # .env 파일 로드 (가능한 경우)
        if load_dotenv:
            load_dotenv()
        
        # .env에서 직접 읽기 (우선순위)
        app_key = os.getenv('KIS_APP_KEY')
        app_secret = os.getenv('KIS_APP_SECRET')
        account_no = os.getenv('KIS_ACCOUNT_NO')
        mock_mode = os.getenv('KIS_MOCK_MODE', 'true').lower() == 'true'
        
        if app_key and app_secret and account_no:
            # .env 파일에서 로드 성공
            self.app_key = app_key
            self.app_secret = app_secret
            self.account_no = account_no
            self.is_mock = mock_mode
            self.base_url = "https://openapi.koreainvestment.com:9443"
        else:
            # settings.yaml에서 로드 (폴백)
            if config_path is None:
                PROJECT_ROOT = Path(__file__).parent.parent.parent
                config_path = str(PROJECT_ROOT / 'config' / 'settings.yaml')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            kis_config = config['kis_api']
            self.app_key = kis_config['app_key']
            self.app_secret = kis_config['app_secret']
            self.account_no = kis_config['account_no']
            self.base_url = kis_config['base_url']
            self.is_mock = kis_config.get('mock_mode', False)
        
        # 접근 토큰
        self.access_token: Optional[str] = None
        
        print(f"\n{'='*70}")
        print(f"🔑 KIS API 클라이언트 초기화")
        print(f"{'='*70}")
        print(f"Base URL: {self.base_url}")
        print(f"계좌번호: {self.account_no}")
        print(f"모드: {'모의투자' if self.is_mock else '실전투자'}")
        print(f"{'='*70}\n")
        
        # 토큰 발급
        self._get_access_token()
    
    # =========================================
    # 인증
    # =========================================
    
    def _get_access_token(self):
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result['access_token']
            
            print(f"✅ 접근 토큰 발급 완료")
            
        except Exception as e:
            print(f"❌ 토큰 발급 실패: {e}")
            # 테스트용 더미 토큰
            self.access_token = "DUMMY_TOKEN_FOR_TEST"
    
    def _get_headers(self, tr_id: str) -> Dict:
        """API 요청 헤더"""
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
    
    # =========================================
    # 주문 (매수/매도)
    # =========================================
    
    def buy_market_order(self, stock_code: str, quantity: int) -> Dict:
        """
        시장가 매수 주문
        
        Args:
            stock_code: 종목코드 (6자리)
            quantity: 수량
            
        Returns:
            주문 결과 {'success': bool, 'order_no': str, ...}
        """
        # 모의투자와 실전투자 TR_ID 다름
        tr_id = "VTTC0802U" if self.is_mock else "TTTC0802U"
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        
        headers = self._get_headers(tr_id)
        
        data = {
            "CANO": self.account_no.split('-')[0],  # 계좌번호 앞 8자리
            "ACNT_PRDT_CD": self.account_no.split('-')[1],  # 계좌상품코드 뒤 2자리
            "PDNO": stock_code,  # 종목코드
            "ORD_DVSN": "01",  # 주문구분 (01: 시장가)
            "ORD_QTY": str(quantity),  # 주문수량
            "ORD_UNPR": "0",  # 주문단가 (시장가는 0)
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            
            result = response.json()
            
            if result['rt_cd'] == '0':  # 성공
                return {
                    'success': True,
                    'order_no': result['output']['ODNO'],  # 주문번호
                    'stock_code': stock_code,
                    'quantity': quantity,
                    'message': result['msg1']
                }
            else:
                return {
                    'success': False,
                    'message': result['msg1']
                }
                
        except Exception as e:
            print(f"❌ 매수 주문 실패: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def sell_market_order(self, stock_code: str, quantity: int) -> Dict:
        """
        시장가 매도 주문
        
        Args:
            stock_code: 종목코드
            quantity: 수량
            
        Returns:
            주문 결과
        """
        # 모의투자와 실전투자 TR_ID 다름
        tr_id = "VTTC0801U" if self.is_mock else "TTTC0801U"
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        
        headers = self._get_headers(tr_id)
        
        data = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0",
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            
            result = response.json()
            
            if result['rt_cd'] == '0':
                return {
                    'success': True,
                    'order_no': result['output']['ODNO'],
                    'stock_code': stock_code,
                    'quantity': quantity,
                    'message': result['msg1']
                }
            else:
                return {
                    'success': False,
                    'message': result['msg1']
                }
                
        except Exception as e:
            print(f"❌ 매도 주문 실패: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    # =========================================
    # 잔고 조회
    # =========================================
    
    def get_balance(self) -> Dict:
        """
        예수금 (현금) 조회
        
        Returns:
            {'cash': float, 'total_assets': float, ...}
        """
        tr_id = "VTTC8908R" if self.is_mock else "TTTC8908R"
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        
        headers = self._get_headers(tr_id)
        
        params = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": "005930",  # 임시 종목코드 (필수값이지만 사용 안 함)
            "ORD_UNPR": "0",
            "ORD_DVSN": "01",
            "CMA_EVLU_AMT_ICLD_YN": "Y",  # CMA 평가금액 포함 여부
            "OVRS_ICLD_YN": "N"  # 해외 포함 여부
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            if result['rt_cd'] == '0':
                output = result['output']
                return {
                    'success': True,
                    'cash': float(output.get('ord_psbl_cash', 0)),  # 주문가능현금
                    'total_assets': float(output.get('nass_amt', 0)),  # 순자산
                }
            else:
                return {
                    'success': False,
                    'message': result['msg1']
                }
                
        except Exception as e:
            print(f"❌ 잔고 조회 실패: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_positions(self) -> list:
        """
        보유 종목 조회
        
        Returns:
            [{'stock_code': str, 'quantity': int, 'avg_price': float, ...}, ...]
        """
        tr_id = "VTTC8434R" if self.is_mock else "TTTC8434R"
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        
        headers = self._get_headers(tr_id)
        
        params = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "AFHR_FLPR_YN": "N",  # 시간외단일가여부
            "OFL_YN": "",  # 오프라인여부
            "INQR_DVSN": "02",  # 조회구분 (01: 대출일별, 02: 종목별)
            "UNPR_DVSN": "01",  # 단가구분
            "FUND_STTL_ICLD_YN": "N",  # 펀드결제분포함여부
            "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
            "PRCS_DVSN": "01",  # 처리구분
            "CTX_AREA_FK100": "",  # 연속조회검색조건100
            "CTX_AREA_NK100": ""  # 연속조회키100
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            if result['rt_cd'] == '0':
                positions = []
                for item in result['output1']:
                    if int(item['hldg_qty']) > 0:  # 보유수량 > 0
                        positions.append({
                            'stock_code': item['pdno'],  # 종목코드
                            'stock_name': item['prdt_name'],  # 종목명
                            'quantity': int(item['hldg_qty']),  # 보유수량
                            'avg_price': float(item['pchs_avg_pric']),  # 매입평균가격
                            'current_price': float(item['prpr']),  # 현재가
                            'eval_amount': float(item['evlu_amt']),  # 평가금액
                            'profit_loss': float(item['evlu_pfls_amt']),  # 평가손익금액
                            'profit_rate': float(item['evlu_pfls_rt'])  # 평가손익률
                        })
                
                return positions
            else:
                print(f"❌ 보유종목 조회 실패: {result['msg1']}")
                return []
                
        except Exception as e:
            print(f"❌ 보유종목 조회 실패: {e}")
            return []
    
    # =========================================
    # 시세 조회
    # =========================================
    
    def get_current_price(self, stock_code: str) -> Optional[float]:
        """
        현재가 조회
        
        Args:
            stock_code: 종목코드
            
        Returns:
            현재가 (실패 시 None)
        """
        tr_id = "FHKST01010100"  # 주식현재가시세
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        
        headers = self._get_headers(tr_id)
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장분류코드 (J: 주식)
            "FID_INPUT_ISCD": stock_code  # 종목코드
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            if result['rt_cd'] == '0':
                return float(result['output']['stck_prpr'])  # 주식현재가
            else:
                return None
                
        except Exception as e:
            print(f"❌ 현재가 조회 실패: {e}")
            return None


# =========================================
# 테스트
# =========================================

def main():
    """테스트 실행"""
    
    # 설정 파일에 실제 API 키가 있어야 함
    client = KISApiClient()
    
    print("\n🧪 KIS API 클라이언트 테스트\n")
    
    # 1. 잔고 조회
    print("1️⃣ 잔고 조회")
    balance = client.get_balance()
    print(f"   결과: {balance}\n")
    
    # 2. 보유 종목 조회
    print("2️⃣ 보유 종목 조회")
    positions = client.get_positions()
    print(f"   보유 종목 수: {len(positions)}개")
    for pos in positions:
        print(f"   - {pos['stock_name']}: {pos['quantity']}주, "
              f"손익 {pos['profit_rate']:.2f}%")
    print()
    
    # 3. 현재가 조회
    print("3️⃣ 현재가 조회 (삼성전자)")
    price = client.get_current_price('005930')
    print(f"   현재가: {price:,.0f}원\n")
    
    # 4. 매수/매도 주문 (테스트는 주석 처리)
    # print("4️⃣ 매수 주문 테스트 (주석 처리)")
    # result = client.buy_market_order('005930', 1)
    # print(f"   결과: {result}\n")


if __name__ == '__main__':
    main()
