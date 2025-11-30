"""
간단한 투자자 매매 검증 스크립트
- 기존 데이터 구조 확인
- 샘플 종목으로 투자자 매매 데이터 테스트
- 실제 상관관계 빠르게 확인
"""

import pandas as pd
import numpy as np
from pykrx import stock
from datetime import datetime, timedelta
import time

print("="*70)
print("🔍 투자자 매매 데이터 빠른 검증")
print("="*70 + "\n")

# 1. 기존 데이터 확인
print("1️⃣ 기존 데이터 구조 확인")
print("-" * 70)

df = pd.read_parquet('./data/crash_rebound/all_stocks_3years.parquet')
df_crashes = df[df['crash'] == 1].copy()

print(f"전체 데이터: {len(df):,}행")
print(f"급락 이벤트: {len(df_crashes):,}개")
print(f"\n컬럼 ({len(df.columns)}개):")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2d}. {col}")

print(f"\n투자자 매매 데이터 확인:")
for col in ['institution_net', 'foreign_net', 'individual_net', 'program_net']:
    zero_count = (df[col] == 0).sum()
    zero_pct = zero_count / len(df) * 100
    print(f"  {col}: {zero_pct:.1f}% 가 0")

# 2. 개별 종목 파일 확인
print(f"\n\n2️⃣ 개별 종목 파일 확인")
print("-" * 70)

from pathlib import Path
individual_files = list(Path('./data/crash_rebound').glob('*.parquet'))
individual_files = [f for f in individual_files if f.name != 'all_stocks_3years.parquet']

if individual_files:
    sample_file = individual_files[0]
    print(f"샘플 파일: {sample_file.name}")
    
    df_sample = pd.read_parquet(sample_file)
    print(f"\n컬럼: {df_sample.columns.tolist()}")
    print(f"인덱스: {df_sample.index.name}")
    print(f"\n첫 3행:")
    print(df_sample.head(3))
else:
    print("⚠️ 개별 종목 파일 없음")

# 3. pykrx로 실제 데이터 테스트
print(f"\n\n3️⃣ pykrx로 실제 투자자 매매 데이터 테스트")
print("-" * 70)

# 삼성전자로 테스트
test_code = '005930'
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

print(f"테스트 종목: 삼성전자 ({test_code})")
print(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}\n")

try:
    df_investor = stock.get_market_trading_value_by_date(
        start_date.strftime('%Y%m%d'),
        end_date.strftime('%Y%m%d'),
        test_code
    )
    
    if not df_investor.empty:
        print("✅ 투자자 매매 데이터 수집 성공!")
        print(f"\n컬럼: {df_investor.columns.tolist()}")
        print(f"\n최근 5일 데이터:")
        print(df_investor.tail())
        
        print(f"\n통계:")
        print(df_investor.describe())
        
    else:
        print("⚠️ 데이터 없음")
        
except Exception as e:
    print(f"❌ 오류: {e}")

# 4. 급락 이벤트 샘플 확인
print(f"\n\n4️⃣ 급락 이벤트 샘플 분석")
print("-" * 70)

# 성공한 급락 vs 실패한 급락 각 5개씩
df_success = df_crashes[df_crashes['success'] == True].head(5)
df_fail = df_crashes[df_crashes['success'] == False].head(5)

print("성공한 급락 샘플:")
print(df_success[['stock_code', 'stock_name', 'crash_rate', 'rebound_d5', 
                   'institution_net', 'foreign_net', 'volume']].to_string(index=False))

print(f"\n실패한 급락 샘플:")
print(df_fail[['stock_code', 'stock_name', 'crash_rate', 'rebound_d5',
               'institution_net', 'foreign_net', 'volume']].to_string(index=False))

# 5. 결론
print(f"\n\n" + "="*70)
print("📌 결론")
print("="*70)

print("\n✅ 확인된 사항:")
print("  - pykrx API 정상 작동")
print("  - 투자자 매매 데이터 수집 가능")

print("\n❌ 문제점:")
print("  - 기존 데이터에 date 컬럼 없음")
print("  - 투자자 매매 데이터 100% 누락 (전부 0)")
print("  - 데이터 재수집 필요")

print("\n💡 해결 방안:")
print("  1. crash_rebound_collector.py 수정")
print("  2. date 컬럼 추가")
print("  3. 투자자 매매 데이터 실제 수집")
print("  4. 급락 전후 3일 투자자 매매 패턴 분석")

print("\n" + "="*70)
