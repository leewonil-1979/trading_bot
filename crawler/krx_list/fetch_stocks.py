"""
KRX 전체 종목 리스트 수집 모듈
네이버 금융에서 코스피/코스닥 종목 리스트를 크롤링합니다.
"""
import requests
import pandas as pd
from datetime import datetime
import json
import time
from bs4 import BeautifulSoup


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
                
                # BeautifulSoup으로 HTML 파싱
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 종목 테이블 찾기
                table = soup.find('table', class_='type_2')
                if not table:
                    break
                
                rows = table.find('tbody').find_all('tr')
                page_stocks = []
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    
                    # 종목명에서 종목코드 추출
                    name_tag = cols[1].find('a')
                    if not name_tag:
                        continue
                    
                    href = name_tag.get('href', '')
                    if 'code=' not in href:
                        continue
                    
                    # 종목코드 추출 (예: code=005930)
                    stock_code = href.split('code=')[1].split('&')[0]
                    stock_name = name_tag.text.strip()
                    
                    # 현재가
                    current_price = cols[2].text.strip().replace(',', '')
                    
                    stock_info = {
                        '종목코드': stock_code,
                        '종목명': stock_name,
                        '현재가': current_price,
                        '시장': market
                    }
                    page_stocks.append(stock_info)
                
                if not page_stocks:
                    break
                
                stocks.extend(page_stocks)
                print(f"  페이지 {page}: {len(page_stocks)}개 종목 수집")
                time.sleep(0.5)  # 서버 부하 방지
                
            except Exception as e:
                print(f"페이지 {page} 처리 중 오류: {e}")
                break
        
        if not stocks:
            return pd.DataFrame()
        
        # DataFrame 생성
        result = pd.DataFrame(stocks)
        
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
        
        # 종목코드는 이미 6자리 형식으로 추출됨
        print(f"\n총 {len(all_stocks)}개 종목 수집 완료")
        print(f"코스피: {len(kospi)}개, 코스닥: {len(kosdaq)}개")
        
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
