"""
pykrx 상세 투자자 데이터 수집기
- 금융투자, 보험, 투신, 사모, 은행, 기타금융, 연기금
- 3년 전체 데이터 수집
"""

import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
from pathlib import Path
import time
import json


class DetailedInvestorCollector:
    """pykrx 상세 투자자 데이터 수집기"""
    
    def __init__(self, data_dir='./data/crash_rebound'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 진행상황 저장
        self.progress_file = self.data_dir / 'detailed_investor_progress.json'
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
    
    def collect_detailed_investor(self, stock_code, start_date, end_date, market='KOSPI'):
        """
        상세 투자자 데이터 수집 (날짜별)
        
        Returns:
            DataFrame with columns:
            - financial_invest_net (금융투자 - 증권사, 프로그램 매매 포함)
            - insurance_net (보험)
            - fund_net (투신 - 펀드)
            - private_fund_net (사모펀드)
            - bank_net (은행)
            - other_finance_net (기타금융)
            - pension_net (연기금 - 국민연금 등)
        """
        try:
            # 날짜별로 수집
            date_range = pd.date_range(start_date, end_date, freq='D')
            
            result = []
            for date in date_range:
                date_str = date.strftime('%Y%m%d')
                try:
                    df = stock.get_market_trading_value_by_investor(
                        date_str,
                        date_str,
                        stock_code
                    )  # type: ignore
                    
                    if df.empty:
                        continue
                    
                    # 순매수만 추출
                    data: dict = {'Date': date}
                    data['financial_invest_net'] = int(df.loc['금융투자', '순매수']) if '금융투자' in df.index else 0  # type: ignore
                    data['insurance_net'] = int(df.loc['보험', '순매수']) if '보험' in df.index else 0  # type: ignore
                    data['fund_net'] = int(df.loc['투신', '순매수']) if '투신' in df.index else 0  # type: ignore
                    data['private_fund_net'] = int(df.loc['사모', '순매수']) if '사모' in df.index else 0  # type: ignore
                    data['bank_net'] = int(df.loc['은행', '순매수']) if '은행' in df.index else 0  # type: ignore
                    data['other_finance_net'] = int(df.loc['기타금융', '순매수']) if '기타금융' in df.index else 0  # type: ignore
                    data['pension_net'] = int(df.loc['연기금 등', '순매수']) if '연기금 등' in df.index else 0  # type: ignore
                    
                    result.append(data)
                except:
                    continue
            
            if not result:
                return None
            
            df_result = pd.DataFrame(result)
            df_result = df_result.set_index('Date')
            
            return df_result
            
        except Exception as e:
            print(f"   ⚠️ 수집 실패: {e}")
            return None
    
    def update_stock_file(self, stock_code, stock_name, market='KOSPI'):
        """기존 개별 파일에 상세 투자자 데이터 추가"""
        
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
            
            print(f"   📊 상세 투자자 데이터 수집 중...", end=' ')
            
            # 상세 투자자 데이터 수집
            df_detailed = self.collect_detailed_investor(stock_code, start_date, end_date, market)
            
            if df_detailed is not None and len(df_detailed) > 0:
                # 기존 데이터에 병합
                for col in df_detailed.columns:
                    for date in df_detailed.index:
                        if date in df.index:
                            df.loc[date, col] = df_detailed.loc[date, col]
                
                # 누락된 값 0으로 채우기
                for col in ['financial_invest_net', 'insurance_net', 'fund_net', 
                           'private_fund_net', 'bank_net', 'other_finance_net', 'pension_net']:
                    if col in df.columns:
                        df[col] = df[col].fillna(0)
                
                print(f"✅ {len(df_detailed)}일")
            else:
                # 데이터 없으면 0으로 채우기
                for col in ['financial_invest_net', 'insurance_net', 'fund_net', 
                           'private_fund_net', 'bank_net', 'other_finance_net', 'pension_net']:
                    df[col] = 0
                print("⚠️ 데이터 없음 - 0으로 채움")
            
            # 저장
            df.reset_index().to_parquet(file_path, index=False)
            
            # 진행상황 저장
            self.save_progress(stock_code)
            
            time.sleep(0.1)  # API 부하 방지
            
            return True
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """전체 파일 업데이트"""
    collector = DetailedInvestorCollector()
    
    # 개별 파일 목록
    data_dir = Path('./data/crash_rebound')
    files = list(data_dir.glob('*.parquet'))
    files = [f for f in files if f.name != 'all_stocks_3years.parquet']
    
    print(f"\n{'='*60}")
    print(f"📊 pykrx 상세 투자자 데이터 수집 시작")
    print(f"총 {len(files)}개 파일")
    print(f"완료: {len(collector.progress['completed'])}개")
    print(f"남은: {len(files) - len(collector.progress['completed'])}개")
    print(f"{'='*60}\n")
    
    print("추가될 데이터 (7개):")
    print("  1. financial_invest_net (금융투자 - 증권사, 프로그램 매매)")
    print("  2. insurance_net (보험)")
    print("  3. fund_net (투신 - 펀드)")
    print("  4. private_fund_net (사모펀드)")
    print("  5. bank_net (은행)")
    print("  6. other_finance_net (기타금융)")
    print("  7. pension_net (연기금 - 국민연금)")
    print(f"{'='*60}\n")
    
    success = 0
    fail = 0
    
    for i, file_path in enumerate(files, 1):
        parts = file_path.stem.split('_')
        if len(parts) < 2:
            continue
        
        stock_code = parts[0]
        stock_name = '_'.join(parts[1:])
        
        # 코스피/코스닥 구분 (간단히 코드로 판단)
        # 코스닥: 숫자 6자리 시작이 특정 범위
        market = 'KOSDAQ' if stock_code.startswith(('A', '0')) and len(stock_code) == 6 else 'KOSPI'
        
        print(f"[{i}/{len(files)}] {stock_name} ({stock_code}) - {market}")
        
        if collector.update_stock_file(stock_code, stock_name, market):
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
    print(f"🎉 상세 투자자 데이터 수집 완료!")
    print(f"성공: {success}, 실패: {fail}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
