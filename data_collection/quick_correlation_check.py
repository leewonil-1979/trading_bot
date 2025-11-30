"""
투자자 매매 vs 반등률 상관관계 빠른 검증
- 개별 파일에서 급락 이벤트 100개 샘플 추출
- pykrx로 투자자 매매 데이터 수집
- 실제 상관관계 분석
- 30분 완료!
"""

import pandas as pd
import numpy as np
from pykrx import stock
from datetime import datetime, timedelta
from pathlib import Path
import time
import json

print("="*70)
print("⚡ 투자자 매매 vs 반등률 빠른 검증 (30분 완료)")
print("="*70 + "\n")

# 1. 개별 파일에서 급락 이벤트 샘플 추출
print("1️⃣ 급락 이벤트 샘플 추출")
print("-" * 70)

crash_rebound_dir = Path('./data/crash_rebound')
individual_files = [f for f in crash_rebound_dir.glob('*.parquet') 
                   if f.name != 'all_stocks_3years.parquet']

print(f"개별 파일: {len(individual_files)}개")

all_crashes = []
target_samples = 200  # 200개 샘플

for file in individual_files[:50]:  # 처음 50개 파일만
    try:
        df = pd.read_parquet(file)
        df_crash = df[df['crash'] == 1].copy()
        
        if len(df_crash) > 0:
            # date 인덱스를 컬럼으로
            df_crash = df_crash.reset_index()
            df_crash['date'] = pd.to_datetime(df_crash['Date'])
            
            for _, row in df_crash.iterrows():
                all_crashes.append({
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name'],
                    'date': row['date'],
                    'crash_rate': row['crash_rate'],
                    'rebound_d5': row['rebound_d5'],
                    'success': row['success'],
                    'volume': row['volume']
                })
                
                if len(all_crashes) >= target_samples:
                    break
        
        if len(all_crashes) >= target_samples:
            break
            
    except Exception as e:
        continue

df_crashes = pd.DataFrame(all_crashes)
print(f"✅ 급락 샘플: {len(df_crashes)}개 추출 완료\n")

# 2. 투자자 매매 데이터 수집
print("2️⃣ 투자자 매매 데이터 수집")
print("-" * 70)

investor_data = []

for idx, row in df_crashes.iterrows():
    if int(idx) % 20 == 0:  # type: ignore
        print(f"진행: {idx}/{len(df_crashes)} ({int(idx)/len(df_crashes)*100:.1f}%)")  # type: ignore
    
    try:
        date_str = row['date'].strftime('%Y%m%d')
        
        # 투자자 매매 조회
        df_investor = stock.get_market_trading_value_by_date(
            date_str, date_str, row['stock_code']
        )
        
        if not df_investor.empty:
            investor_data.append({
                'stock_code': row['stock_code'],
                'date': row['date'],
                'institution_net': int(df_investor['기관합계'].iloc[0]) if '기관합계' in df_investor.columns else 0,  # type: ignore
                'foreign_net': int(df_investor['외국인합계'].iloc[0]) if '외국인합계' in df_investor.columns else 0,  # type: ignore
                'individual_net': df_investor['개인'].iloc[0] if '개인' in df_investor.columns else 0,
            })
        
        time.sleep(0.1)  # API 제한
        
    except Exception as e:
        continue

df_investor = pd.DataFrame(investor_data)
print(f"\n✅ 투자자 매매: {len(df_investor)}개 수집 완료\n")

# 3. 데이터 병합
print("3️⃣ 데이터 병합")
print("-" * 70)

df_merged = df_crashes.merge(
    df_investor,
    on=['stock_code', 'date'],
    how='left'
)

# 결측치 0으로
for col in ['institution_net', 'foreign_net', 'individual_net']:
    df_merged[col] = df_merged[col].fillna(0)

print(f"병합 완료: {len(df_merged)}행\n")

# 4. 상관관계 분석
print("="*70)
print("📊 투자자 매매 vs 반등률 상관관계 분석")
print("="*70 + "\n")

# 4-1. 외국인 순매수 구간별
print("1️⃣ 외국인 순매수 vs 반등률")
print("-" * 70)

df_merged['foreign_group'] = pd.cut(
    df_merged['foreign_net'] / 100000000,
    bins=[-np.inf, -50, -10, 0, 10, 50, np.inf],
    labels=['대량 매도 (-50억+)', '매도 (-10~50억)', '소폭 매도', '매수', '적극 매수 (+10~50억)', '대량 매수 (+50억+)']
)

result = df_merged.groupby('foreign_group').agg({
    'success': ['count', 'sum', 'mean'],
    'rebound_d5': 'mean'
})

result.columns = ['건수', '성공', '성공률', '평균 반등률']
result['성공률'] = (result['성공률'] * 100).round(1)
result['평균 반등률'] = (result['평균 반등률'] * 100).round(2)

print(result)
print()

# 4-2. 기관 순매수 구간별
print("2️⃣ 기관 순매수 vs 반등률")
print("-" * 70)

df_merged['institution_group'] = pd.cut(
    df_merged['institution_net'] / 100000000,
    bins=[-np.inf, -30, -10, 0, 10, 30, np.inf],
    labels=['대량 매도', '매도', '소폭 매도', '매수', '적극 매수', '대량 매수']
)

result2 = df_merged.groupby('institution_group').agg({
    'success': ['count', 'sum', 'mean'],
    'rebound_d5': 'mean'
})

result2.columns = ['건수', '성공', '성공률', '평균 반등률']
result2['성공률'] = (result2['성공률'] * 100).round(1)
result2['평균 반등률'] = (result2['평균 반등률'] * 100).round(2)

print(result2)
print()

# 4-3. 핵심 결론
print("="*70)
print("🎯 핵심 결론")
print("="*70 + "\n")

# 외국인 대량 매도 vs 나머지
foreign_sell = df_merged[df_merged['foreign_net'] < -5000000000]
foreign_other = df_merged[df_merged['foreign_net'] >= -5000000000]

print(f"외국인 대량 매도 (-50억 이상):")
if len(foreign_sell) > 0:
    print(f"  건수: {len(foreign_sell)}개")
    print(f"  성공률: {foreign_sell['success'].mean()*100:.1f}%")
    print(f"  평균 반등: {foreign_sell['rebound_d5'].mean()*100:.2f}%")
else:
    print(f"  데이터 없음")

print(f"\n나머지:")
print(f"  건수: {len(foreign_other)}개")
print(f"  성공률: {foreign_other['success'].mean()*100:.1f}%")
print(f"  평균 반등: {foreign_other['rebound_d5'].mean()*100:.2f}%")

# 결과 저장
print(f"\n\n💾 결과 저장")
print("-" * 70)

output_file = './data/enhanced/quick_verification_result.parquet'
df_merged.to_parquet(output_file)
print(f"✅ {output_file}")

analysis_result = {
    'foreign_analysis': result.to_dict(),
    'institution_analysis': result2.to_dict(),
    'sample_count': len(df_merged),
    'data_collected': len(df_investor)
}

json_file = './data/enhanced/quick_verification_analysis.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(analysis_result, f, ensure_ascii=False, indent=2, default=str)
print(f"✅ {json_file}")

print(f"\n" + "="*70)
print("✅ 검증 완료!")
print("="*70)
