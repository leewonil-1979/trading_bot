"""
상세 투자자 데이터 통합 파일 생성
- 개별 parquet 파일들을 하나의 통합 파일로 병합
- 48개 컬럼 (기존 40개 + 새로운 7개 + 날짜)
"""
import pandas as pd
from pathlib import Path
from datetime import datetime


def consolidate_all_stocks():
    """모든 종목 데이터를 통합 파일로 병합"""
    
    data_dir = Path('./data/crash_rebound')
    output_file = data_dir / 'all_stocks_3years.parquet'
    
    # 개별 파일 목록
    stock_files = list(data_dir.glob('*_*.parquet'))
    stock_files = [f for f in stock_files if f.name != 'all_stocks_3years.parquet']
    
    print(f"\n{'='*60}")
    print(f"📊 통합 데이터 파일 생성")
    print(f"{'='*60}")
    print(f"개별 파일 수: {len(stock_files)}개")
    print(f"출력 파일: {output_file}")
    print(f"{'='*60}\n")
    
    all_data = []
    
    for i, file_path in enumerate(stock_files, 1):
        try:
            # 파일 로드
            df = pd.read_parquet(file_path)
            
            # 종목 정보 추가
            parts = file_path.stem.split('_')
            if len(parts) >= 2:
                stock_code = parts[0]
                stock_name = '_'.join(parts[1:])
                
                df['stock_code'] = stock_code
                df['stock_name'] = stock_name
                
                all_data.append(df)
                
                if i % 100 == 0:
                    print(f"[{i}/{len(stock_files)}] 로드 중... (총 {sum(len(d) for d in all_data):,}행)")
                    
        except Exception as e:
            print(f"❌ {file_path.name}: {e}")
    
    print(f"\n✅ 모든 파일 로드 완료")
    print(f"총 {len(all_data)}개 종목")
    
    # 통합
    print("\n🔄 데이터 병합 중...")
    df_all = pd.concat(all_data, ignore_index=False)
    
    # 인덱스를 컬럼으로 변환
    df_all = df_all.reset_index()
    
    # Date 컬럼 확인 및 정리
    if 'index' in df_all.columns and 'Date' not in df_all.columns:
        df_all = df_all.rename(columns={'index': 'Date'})
    elif 'index' in df_all.columns and 'Date' in df_all.columns:
        df_all = df_all.drop(columns=['index'])
    
    # 정렬
    if 'Date' in df_all.columns:
        df_all = df_all.sort_values(['stock_code', 'Date'])
    else:
        df_all = df_all.sort_values('stock_code')
    
    print(f"\n📊 통합 데이터 정보:")
    print(f"   - 총 행 수: {len(df_all):,}")
    print(f"   - 총 컬럼 수: {len(df_all.columns)}")
    print(f"   - 종목 수: {df_all['stock_code'].nunique()}")
    print(f"   - 날짜 범위: {df_all['Date'].min()} ~ {df_all['Date'].max()}")
    
    # 컬럼 확인
    new_cols = ['financial_invest_net', 'insurance_net', 'fund_net', 
                'private_fund_net', 'bank_net', 'other_finance_net', 'pension_net']
    
    print(f"\n✅ 새로운 컬럼:")
    for col in new_cols:
        if col in df_all.columns:
            non_zero = (df_all[col] != 0).sum()
            pct = non_zero / len(df_all) * 100
            print(f"   {col}: {non_zero:,} / {len(df_all):,} ({pct:.1f}%)")
        else:
            print(f"   ❌ {col}: 없음")
    
    # 저장
    print(f"\n💾 파일 저장 중: {output_file}")
    df_all.to_parquet(output_file, index=False, compression='snappy')
    
    # 파일 크기 확인
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"✅ 저장 완료! (크기: {file_size_mb:.1f} MB)")
    
    print(f"\n{'='*60}")
    print(f"🎉 통합 파일 생성 완료!")
    print(f"{'='*60}\n")
    
    return df_all


def verify_data_quality(df):
    """데이터 품질 검증"""
    
    print(f"\n{'='*60}")
    print(f"🔍 데이터 품질 검증")
    print(f"{'='*60}\n")
    
    # 1. 기본 정보
    print("1. 기본 정보")
    print(f"   - 전체 행 수: {len(df):,}")
    print(f"   - 전체 컬럼 수: {len(df.columns)}")
    print(f"   - 종목 수: {df['stock_code'].nunique()}")
    print(f"   - 메모리 사용량: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    
    # 2. 결측치 확인
    print(f"\n2. 결측치 (상위 5개)")
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False).head()
    if len(missing) > 0:
        for col, count in missing.items():
            pct = count / len(df) * 100
            print(f"   {col}: {count:,} ({pct:.1f}%)")
    else:
        print("   ✅ 결측치 없음")
    
    # 3. 급락 이벤트 통계
    print(f"\n3. 급락 이벤트")
    crashes = df[df['crash'] == 1]
    print(f"   - 급락 이벤트 수: {len(crashes):,}")
    print(f"   - 급락률: {len(crashes) / len(df) * 100:.2f}%")
    
    if 'success' in df.columns:
        success_rate = crashes['success'].mean() * 100
        print(f"   - 반등 성공률: {success_rate:.1f}%")
    
    # 4. 새로운 투자자 데이터 통계
    print(f"\n4. 상세 투자자 데이터")
    new_cols = ['financial_invest_net', 'fund_net', 'pension_net']
    for col in new_cols:
        if col in df.columns:
            non_zero = (df[col] != 0).sum()
            pct = non_zero / len(df) * 100
            mean_val = df[df[col] != 0][col].mean()
            print(f"   {col}:")
            print(f"      데이터율: {pct:.1f}%")
            print(f"      평균값: {mean_val:,.0f}")
    
    # 5. 종목별 통계
    print(f"\n5. 종목별 데이터 수")
    stock_counts = df.groupby('stock_code').size()
    print(f"   - 평균: {stock_counts.mean():.0f}일")
    print(f"   - 최소: {stock_counts.min()}일")
    print(f"   - 최대: {stock_counts.max()}일")
    
    print(f"\n{'='*60}")
    print(f"✅ 검증 완료")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    # 통합 파일 생성
    df = consolidate_all_stocks()
    
    # 품질 검증
    verify_data_quality(df)
    
    print("\n다음 단계:")
    print("1. 상관관계 분석: python analysis/correlation_analysis.py")
    print("2. AI 모델 재학습: python ai_model/train_crash_rebound.py")
