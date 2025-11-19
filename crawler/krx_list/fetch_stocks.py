"""
KRX 전체 종목 리스트 수집 모듈
네이버 금융에서 코스피/코스닥 종목 리스트를 크롤링합니다.
"""
import requests
import pandas as pd
from datetime import datetime
import json
import time


class KRXStockFetcher:
    """KRX 종목 리스트 수집 클래스"""
    
    def __init__(self):
        self.kospi_url = "https://finance.naver.com/sise/sise_market_sum.naver?&page={}"
        self.kosdaq_url = "https://finance.naver.com/sise/sise_market_sum.naver?sosok=1&page={}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def fetch_market_stocks(self, market='KOSPI', max_pages=50):
        """
        특정 시장의 종목 리스트 수집
        
        Args:
            market (str): 'KOSPI' 또는 'KOSDAQ'
            max_pages (int): 수집할 최대 페이지 수
            
        Returns:
            pd.DataFrame: 종목 정보 데이터프레임
        """
        url = self.kospi_url if market == 'KOSPI' else self.kosdaq_url
        stocks = []
        
        print(f"[{market}] 종목 리스트 수집 중...")
        
        for page in range(1, max_pages + 1):
            try:
                response = requests.get(url.format(page), headers=self.headers, timeout=10)
                
                if response.status_code != 200:
                    print(f"페이지 {page} 요청 실패: {response.status_code}")
                    break
                
                # pandas로 HTML 테이블 파싱
                tables = pd.read_html(response.text)
                
                if not tables:
                    break
                    
                df = tables[1]  # 종목 정보가 있는 테이블
                
                # 유효한 데이터만 필터링
                df = df[df['종목명'].notna()]
                
                if df.empty:
                    break
                
                stocks.append(df)
                print(f"  페이지 {page}: {len(df)}개 종목 수집")
                time.sleep(0.5)  # 서버 부하 방지
                
            except Exception as e:
                print(f"페이지 {page} 처리 중 오류: {e}")
                break
        
        if not stocks:
            return pd.DataFrame()
        
        # 전체 데이터 병합
        result = pd.concat(stocks, ignore_index=True)
        result['시장'] = market
        
        print(f"[{market}] 총 {len(result)}개 종목 수집 완료\n")
        return result
    
    def fetch_all_stocks(self):
        """
        코스피 + 코스닥 전체 종목 수집
        
        Returns:
            pd.DataFrame: 전체 종목 정보
        """
        kospi = self.fetch_market_stocks('KOSPI')
        kosdaq = self.fetch_market_stocks('KOSDAQ')
        
        all_stocks = pd.concat([kospi, kosdaq], ignore_index=True)
        
        # 종목코드 정제 (6자리 숫자로 변환)
        if '종목코드' in all_stocks.columns:
            all_stocks['종목코드'] = all_stocks['종목코드'].astype(str).str.zfill(6)
        
        return all_stocks
    
    def save_to_csv(self, df, output_path='../../data/raw/stock_list.csv'):
        """
        종목 리스트를 CSV로 저장
        
        Args:
            df (pd.DataFrame): 저장할 데이터프레임
            output_path (str): 저장 경로
        """
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"종목 리스트 저장 완료: {output_path}")
        print(f"총 {len(df)}개 종목")
        
    def save_to_json(self, df, output_path='../../data/raw/stock_list.json'):
        """
        종목 리스트를 JSON으로 저장
        
        Args:
            df (pd.DataFrame): 저장할 데이터프레임
            output_path (str): 저장 경로
        """
        # 필수 컬럼만 추출
        stock_dict = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_count': len(df),
            'stocks': df[['종목코드', '종목명', '시장']].to_dict('records')
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stock_dict, f, ensure_ascii=False, indent=2)
        
        print(f"종목 리스트 JSON 저장 완료: {output_path}")


def main():
    """메인 실행 함수"""
    fetcher = KRXStockFetcher()
    
    # 전체 종목 수집
    stocks = fetcher.fetch_all_stocks()
    
    # 저장
    fetcher.save_to_csv(stocks)
    fetcher.save_to_json(stocks)
    
    # 통계 출력
    print("\n=== 수집 통계 ===")
    print(stocks['시장'].value_counts())
    

if __name__ == '__main__':
    main()
