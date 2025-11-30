"""
투자자별 매매 vs 리바운드 성공률 상관관계 분석
- 금융투자, 연기금, 펀드 등 상세 투자자 데이터 분석
- 급락 시점 투자자 행동 패턴 분석
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


def analyze_investor_correlation():
    """투자자 데이터와 리바운드 성공률 상관관계 분석"""
    
    # 데이터 로드
    data_file = Path('./data/crash_rebound/all_stocks_3years.parquet')
    print(f"\n{'='*80}")
    print(f"투자자 매매 vs 리바운드 성공률 상관관계 분석")
    print(f"{'='*80}\n")
    print(f"데이터 로드: {data_file}")
    
    df = pd.read_parquet(data_file)
    
    print(f"전체 데이터: {len(df):,}행")
    print(f"종목 수: {df['stock_code'].nunique()}")
    print()
    
    # 급락 이벤트만 필터링
    crashes = df[df['crash'] == 1].copy()
    print(f"급락 이벤트: {len(crashes):,}건 ({len(crashes)/len(df)*100:.2f}%)")
    
    if 'success' in crashes.columns:
        success_rate = crashes['success'].mean() * 100
        print(f"반등 성공률: {success_rate:.1f}%")
    print()
    
    # 분석할 투자자 컬럼
    investor_cols = [
        'foreign_net',           # 외국인
        'institution_net',       # 기관
        'individual_net',        # 개인
        'financial_invest_net',  # 금융투자 (프로그램 매매 포함)
        'insurance_net',         # 보험
        'fund_net',              # 투신/펀드
        'private_fund_net',      # 사모펀드
        'bank_net',              # 은행
        'other_finance_net',     # 기타금융
        'pension_net'            # 연기금
    ]
    
    # 리바운드 컬럼
    rebound_cols = ['rebound_d1', 'rebound_d2', 'rebound_d5', 'success']
    
    # 사용 가능한 컬럼만 필터링
    available_investor_cols = [col for col in investor_cols if col in crashes.columns]
    available_rebound_cols = [col for col in rebound_cols if col in crashes.columns]
    
    print(f"분석 가능한 투자자 데이터: {len(available_investor_cols)}개")
    print(f"리바운드 지표: {len(available_rebound_cols)}개")
    print()
    
    # === 1. 전체 상관관계 매트릭스 ===
    print("="*80)
    print("1. 투자자 매매 vs 리바운드 상관관계")
    print("="*80)
    
    analysis_cols = available_investor_cols + available_rebound_cols
    corr_data = crashes[analysis_cols].copy()
    
    # 결측치 제거
    corr_data = corr_data.dropna()
    
    # 상관계수 계산
    correlation_matrix = corr_data.corr()
    
    # 투자자 vs 리바운드 상관관계 추출
    investor_rebound_corr = correlation_matrix.loc[available_investor_cols, available_rebound_cols]
    
    print("\n투자자별 리바운드 상관계수:")
    print(investor_rebound_corr.to_string())
    print()
    
    # Success와 가장 높은 상관관계
    if 'success' in available_rebound_cols:
        success_corr = investor_rebound_corr['success'].sort_values(ascending=False)
        print("\n반등 성공과 상관관계 순위:")
        for investor, corr_val in success_corr.items():
            print(f"  {investor:25s}: {corr_val:7.4f}")
    
    # === 2. 투자자별 급락일 평균 순매수 ===
    print("\n" + "="*80)
    print("2. 급락일 투자자별 평균 순매수 (단위: 억원)")
    print("="*80)
    
    for col in available_investor_cols:
        mean_val = crashes[col].mean() / 100_000_000  # 억원 단위
        median_val = crashes[col].median() / 100_000_000
        print(f"  {col:25s}: 평균 {mean_val:10,.0f}억  중앙값 {median_val:10,.0f}억")
    
    # === 3. 성공/실패 그룹별 투자자 행동 비교 ===
    if 'success' in crashes.columns:
        print("\n" + "="*80)
        print("3. 반등 성공/실패 그룹별 투자자 순매수 비교")
        print("="*80)
        
        success_group = crashes[crashes['success'] == 1]
        fail_group = crashes[crashes['success'] == 0]
        
        print(f"\n성공 그룹: {len(success_group)}건")
        print(f"실패 그룹: {len(fail_group)}건")
        print()
        
        comparison = []
        for col in available_investor_cols:
            success_mean = success_group[col].mean() / 100_000_000
            fail_mean = fail_group[col].mean() / 100_000_000
            diff = success_mean - fail_mean
            
            comparison.append({
                'investor': col,
                'success_avg': success_mean,
                'fail_avg': fail_mean,
                'difference': diff
            })
        
        comp_df = pd.DataFrame(comparison)
        comp_df = comp_df.sort_values('difference', ascending=False)
    else:
        comp_df = pd.DataFrame()
    
    if not comp_df.empty:
        print("투자자별 순매수 차이 (성공 - 실패, 단위: 억원):")
        for _, row in comp_df.iterrows():
            print(f"  {row['investor']:25s}: "
                  f"성공 {row['success_avg']:8,.0f}억  "
                  f"실패 {row['fail_avg']:8,.0f}억  "
                  f"차이 {row['difference']:+8,.0f}억")
    
    # === 4. 투자자 순매수 구간별 성공률 ===
    print("\n" + "="*80)
    print("4. 투자자 순매수 구간별 반등 성공률")
    print("="*80)
    
    for col in ['financial_invest_net', 'pension_net', 'foreign_net']:
        if col not in available_investor_cols or 'success' not in crashes.columns:
            continue
        
        # 순매수를 5개 구간으로 나눔
        crashes_with_data = crashes[crashes[col] != 0].copy()
        
        if len(crashes_with_data) == 0:
            continue
        
        crashes_with_data['quartile'] = pd.qcut(
            crashes_with_data[col], 
            q=5, 
            labels=['매도 강', '매도 약', '중립', '매수 약', '매수 강'],
            duplicates='drop'
        )
        
        success_by_quartile = crashes_with_data.groupby('quartile')['success'].agg(['mean', 'count'])
        success_by_quartile['mean'] = success_by_quartile['mean'] * 100
        
        print(f"\n{col}:")
        for idx, row in success_by_quartile.iterrows():
            print(f"  {idx:10s}: {row['mean']:5.1f}% ({int(row['count'])}건)")
    
    # === 5. 시각화 ===
    print("\n" + "="*80)
    print("5. 시각화 생성 중...")
    print("="*80)
    
    output_dir = Path('./analysis/output')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 5-1. 상관관계 히트맵
    plt.figure(figsize=(12, 10))
    sns.heatmap(
        investor_rebound_corr, 
        annot=True, 
        fmt='.3f', 
        cmap='RdYlGn',
        center=0,
        vmin=-0.3,
        vmax=0.3
    )
    plt.title('Investor Net Buy vs Rebound Success Correlation', fontsize=14, pad=20)
    plt.tight_layout()
    plt.savefig(output_dir / 'investor_rebound_correlation.png', dpi=150, bbox_inches='tight')
    print(f"  ✅ {output_dir / 'investor_rebound_correlation.png'}")
    plt.close()
    
    # 5-2. 성공/실패 그룹 비교 막대그래프
    if 'success' in crashes.columns:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(comp_df))
        width = 0.35
        
        ax.bar(x - width/2, comp_df['success_avg'], width, label='Success', alpha=0.8)
        ax.bar(x + width/2, comp_df['fail_avg'], width, label='Fail', alpha=0.8)
        
        ax.set_xlabel('Investor Type')
        ax.set_ylabel('Average Net Buy (100M KRW)')
        ax.set_title('Investor Behavior: Success vs Fail Groups')
        ax.set_xticks(x)
        ax.set_xticklabels(comp_df['investor'], rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'success_fail_comparison.png', dpi=150, bbox_inches='tight')
        print(f"  ✅ {output_dir / 'success_fail_comparison.png'}")
        plt.close()
    
    print(f"\n{'='*80}")
    print(f"✅ 상관관계 분석 완료!")
    print(f"{'='*80}\n")
    
    return correlation_matrix, comp_df


def generate_summary_report(correlation_matrix, comparison_df):
    """분석 결과 요약 리포트"""
    
    output_dir = Path('./analysis/output')
    report_file = output_dir / 'investor_analysis_summary.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("투자자 매매 vs 리바운드 성공률 상관관계 분석 요약\n")
        f.write("="*80 + "\n\n")
        
        f.write("주요 발견사항:\n\n")
        
        # 상관관계 Top 3
        if 'success' in correlation_matrix.columns:
            success_corr = correlation_matrix['success'].sort_values(ascending=False)
            success_corr = success_corr[success_corr.index != 'success']
            
            f.write("1. 반등 성공과 가장 높은 상관관계:\n")
            for i, (investor, corr) in enumerate(success_corr.head(3).items(), 1):
                f.write(f"   {i}. {investor}: {corr:.4f}\n")
            f.write("\n")
        
        # 성공/실패 그룹 차이 Top 3
        if comparison_df is not None:
            f.write("2. 성공/실패 그룹 순매수 차이 (Top 3):\n")
            for i, row in comparison_df.head(3).iterrows():
                f.write(f"   {i+1}. {row['investor']}: {row['difference']:+,.0f}억원\n")
            f.write("\n")
        
        f.write("="*80 + "\n")
    
    print(f"✅ 요약 리포트 저장: {report_file}\n")


if __name__ == '__main__':
    corr_matrix, comp_df = analyze_investor_correlation()
    generate_summary_report(corr_matrix, comp_df)
    
    print("다음 단계:")
    print("  python ai_model/train_crash_rebound.py  # AI 모델 재학습")
