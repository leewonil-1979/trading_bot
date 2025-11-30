"""
전체 종목 급락 데이터 수집 (개선 버전)
- 일반주 + 우선주 포함
- 거래량 10만주 이상만 (실전 매매 가능)
- 급락 이력 있는 종목만
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_collection.crash_rebound_collector import CrashReboundDataCollector
import time

def main():
    """효율적인 전체 종목 수집"""
    
    print("\n" + "="*80)
    print("🚀 전체 종목 급락 데이터 수집 (일반주 + 우선주)")
    print("="*80 + "\n")
    
    print("📌 수집 전략:")
    print("   1. 전체 종목 대상 (코스피 + 코스닥)")
    print("   2. 거래량 10만주 미만 제외 (실전 매매 불가)")
    print("   3. 급락 이력 있는 종목만 저장")
    print("   4. 3년 데이터 (2022-11-25 ~ 2025-11-24)")
    print()
    
    # 수집기 생성
    collector = CrashReboundDataCollector(output_dir='./data/crash_rebound')
    
    # 전체 종목 수집
    print("⏳ 수집 시작... (예상 시간: 30분 ~ 1시간)")
    print("   - 종목당 약 1초 대기 (API 제한)")
    print("   - 2000개 종목 × 1초 = 약 33분")
    print()
    
    start_time = time.time()
    
    df_all = collector.collect_all_stocks(
        max_stocks=None,  # 전체 종목
        crash_only=True   # 급락 이력 있는 종목만
    )
    
    elapsed = time.time() - start_time
    
    if df_all is not None:
        print("\n" + "="*80)
        print("🎉 데이터 수집 완료!")
        print("="*80 + "\n")
        
        print(f"⏱️ 소요 시간: {elapsed/60:.1f}분")
        print()
        
        print("📊 수집 결과:")
        print(f"   총 데이터: {len(df_all):,}행")
        print(f"   총 급락: {df_all['crash'].sum():,}회")
        print(f"   성공 반등: {df_all['success'].sum():,}회")
        print(f"   성공률: {df_all['success'].sum() / df_all['crash'].sum() * 100:.1f}%")
        print()
        
        print("💾 저장 위치:")
        print("   ./data/crash_rebound/all_stocks_3years.parquet")
        print("   ./data/crash_rebound/collection_stats.json")
        print()
        
        print("다음 단계:")
        print("   1. AI 모델 재학습 (python ai_model/train_crash_rebound.py)")
        print("   2. 전략 최적화 (python ai_model/optimize_strategy.py)")
        print()
    else:
        print("\n❌ 데이터 수집 실패")


if __name__ == '__main__':
    main()
