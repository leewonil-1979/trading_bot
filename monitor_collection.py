"""
데이터 수집 진행 상황 모니터링 및 결과 시각화
"""
import json
import time
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

plt.rcParams['font.family'] = 'DejaVu Sans'
sns.set_style('whitegrid')

def check_progress():
    """수집 진행 상황 확인"""
    progress_file = Path('./data/crash_rebound/collection_progress.json')
    
    if not progress_file.exists():
        return None
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        progress = json.load(f)
    
    return progress

def visualize_results():
    """수집 결과 시각화"""
    
    # 통계 로드
    stats_file = Path('./data/crash_rebound/collection_stats.json')
    if not stats_file.exists():
        print("❌ 통계 파일 없음")
        return
    
    with open(stats_file, 'r', encoding='utf-8') as f:
        stats = json.load(f)
    
    # 전체 데이터 로드
    data_file = Path('./data/crash_rebound/all_stocks_3years.parquet')
    if not data_file.exists():
        print("❌ 데이터 파일 없음")
        return
    
    df = pd.read_parquet(data_file)
    df = df.reset_index()  # 인덱스를 컬럼으로 변환
    
    # 시각화
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'Data Collection Results - {stats["collection_date"]}', 
                 fontsize=16, fontweight='bold')
    
    # 1. 급락 분포
    crash_data = df[df['crash'] == 1]
    axes[0, 0].hist(crash_data['change_pct'], bins=50, color='red', alpha=0.7)
    axes[0, 0].set_title(f'Crash Distribution (Total: {len(crash_data):,})')
    axes[0, 0].set_xlabel('Change %')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].axvline(-10, color='black', linestyle='--', label='-10% threshold')
    axes[0, 0].legend()
    
    # 2. 반등 성공률
    success_rate = stats['success_rate']
    fail_rate = 100 - success_rate
    axes[0, 1].pie([success_rate, fail_rate], 
                   labels=[f'Success\n{success_rate:.1f}%', f'Fail\n{fail_rate:.1f}%'],
                   colors=['green', 'red'], autopct='%1.1f%%', startangle=90)
    axes[0, 1].set_title(f'Rebound Success Rate\n({stats["successful_rebounds"]:,}/{stats["total_crashes"]:,})')
    
    # 3. 종목별 급락 횟수 (상위 20개)
    stock_crashes = df[df['crash'] == 1].groupby(['stock_code', 'stock_name']).size().sort_values(ascending=False).head(20)
    axes[0, 2].barh(range(len(stock_crashes)), stock_crashes.values, color='orange')
    axes[0, 2].set_yticks(range(len(stock_crashes)))
    axes[0, 2].set_yticklabels([f"{name[:8]}" for code, name in stock_crashes.index], fontsize=8)
    axes[0, 2].set_xlabel('Number of Crashes')
    axes[0, 2].set_title('Top 20 Stocks by Crash Count')
    axes[0, 2].invert_yaxis()
    
    # 4. 월별 급락 발생
    if 'Date' in df.columns:
        date_col = 'Date'
    elif 'date' in df.columns:
        date_col = 'date'
    else:
        date_col = df.columns[0]  # 첫 번째 컬럼이 날짜일 것으로 추정
    
    df[date_col] = pd.to_datetime(df[date_col])
    monthly_crashes = df[df['crash'] == 1].groupby(df[date_col].dt.to_period('M')).size()
    axes[1, 0].bar(range(len(monthly_crashes)), monthly_crashes.values, color='purple')
    axes[1, 0].set_title('Monthly Crash Distribution')
    axes[1, 0].set_xlabel('Month')
    axes[1, 0].set_ylabel('Number of Crashes')
    axes[1, 0].set_xticks(range(0, len(monthly_crashes), 3))
    axes[1, 0].set_xticklabels([str(monthly_crashes.index[i]) for i in range(0, len(monthly_crashes), 3)], 
                                rotation=45, fontsize=8)
    
    # 5. 볼륨 분포
    axes[1, 1].hist(df['volume'], bins=50, color='blue', alpha=0.7)
    axes[1, 1].set_title('Volume Distribution')
    axes[1, 1].set_xlabel('Volume')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].set_yscale('log')
    
    # 6. 수집 통계 요약
    axes[1, 2].axis('off')
    summary_text = f"""
    Collection Summary
    {'='*40}
    
    Period: {stats['period']}
    
    Total Stocks: {stats['total_stocks']:,}
    Total Data Points: {stats['total_rows']:,}
    
    Total Crashes: {stats['total_crashes']:,}
    Successful Rebounds: {stats['successful_rebounds']:,}
    Success Rate: {stats['success_rate']:.2f}%
    
    Average per Stock: {stats['total_rows'] / stats['total_stocks']:.0f} days
    Crash per Stock: {stats['total_crashes'] / stats['total_stocks']:.1f}
    
    File Size: {data_file.stat().st_size / 1024 / 1024:.1f} MB
    """
    axes[1, 2].text(0.1, 0.5, summary_text, fontsize=11, 
                   verticalalignment='center', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # 저장
    output_file = './data/crash_rebound/collection_visualization.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ 시각화 저장: {output_file}")
    
    return output_file

def monitor():
    """수집 모니터링"""
    print("\n" + "="*60)
    print("📊 데이터 수집 모니터링 시작")
    print("="*60 + "\n")
    
    last_count = 0
    
    while True:
        progress = check_progress()
        
        if progress:
            current_count = progress['total_completed']
            
            if current_count != last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"진행: {current_count:,}/2,784 종목 ({current_count/2784*100:.1f}%)")
                last_count = current_count
            
            # 완료 확인 (2,784개 또는 5분간 변화 없음)
            if current_count >= 2784:
                print("\n" + "="*60)
                print("🎉 데이터 수집 완료!")
                print("="*60 + "\n")
                break
        
        time.sleep(10)  # 10초마다 확인
    
    # 결과 시각화
    print("\n📊 결과 시각화 중...")
    viz_file = visualize_results()
    
    if viz_file:
        print(f"\n✅ 시각화 완료: {viz_file}")
        print("\n다음 명령으로 이미지를 확인하세요:")
        print(f"   xdg-open {viz_file}")

if __name__ == '__main__':
    monitor()
