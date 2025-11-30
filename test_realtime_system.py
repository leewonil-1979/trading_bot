"""
실시간 학습 시스템 테스트

1. 최근 급락 종목 찾기
2. 종목별 최적 익절/손절 계산
3. 데이터 병합 시뮬레이션
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from auto_trading.realtime_learning_updater import RealtimeLearningUpdater


def test_crash_detection():
    """급락 감지 테스트"""
    print("\n" + "="*70)
    print("🔍 TEST 1: 급락 감지 및 데이터 수집")
    print("="*70 + "\n")
    
    updater = RealtimeLearningUpdater()
    
    # 테스트용 종목 (주요 대형주)
    test_stocks = [
        ('005930', '삼성전자'),
        ('000660', 'SK하이닉스'),
        ('035420', 'NAVER'),
        ('051910', 'LG화학'),
        ('005380', '현대차'),
    ]
    
    crash_count = 0
    
    for code, name in test_stocks:
        print(f"📊 [{name}] 분석 중...")
        crash = updater.detect_realtime_crash(code, name)
        
        if crash:
            crash_count += 1
            print(f"   ✅ 급락 감지: {crash['crash_rate']:.1f}%")
            
            # 저장 테스트
            updater.save_daily_crash(crash)
        else:
            print(f"   ℹ️  정상 (급락 없음)")
    
    print(f"\n📊 급락 종목: {crash_count}/{len(test_stocks)}개")
    
    return crash_count > 0


def test_optimization():
    """최적화 테스트 (실제 데이터 사용)"""
    print("\n" + "="*70)
    print("🎯 TEST 2: 종목별 최적 익절/손절 계산")
    print("="*70 + "\n")
    
    updater = RealtimeLearningUpdater()
    
    # 학습 데이터에서 실제 급락 종목 찾기
    data_path = PROJECT_ROOT / 'data' / 'crash_rebound' / 'all_stocks_3years.parquet'
    
    if not data_path.exists():
        print("❌ 학습 데이터 없음")
        return False
    
    df = pd.read_parquet(data_path)
    
    # 급락률 상위 5개 종목
    df_crashes = df[df['crash_rate'] <= -10.0].copy()
    df_crashes = df_crashes.sort_values('crash_rate').head(5)
    
    print(f"📊 분석 대상: 급락률 상위 5개 종목\n")
    
    for idx, row in df_crashes.iterrows():
        stock_code = row['stock_code']
        stock_name = row.get('stock_name', stock_code)
        crash_rate = row['crash_rate']
        crash_date = row['Date']
        
        print(f"\n{'='*70}")
        print(f"📈 {stock_name} ({stock_code})")
        print(f"   급락일: {crash_date}")
        print(f"   급락률: {crash_rate:.1f}%")
        print(f"{'='*70}")
        
        # 최적화 계산
        crash_data = {
            'stock_code': stock_code,
            'Date': crash_date,
            'Close': row['Close'],
            'crash_rate': crash_rate
        }
        
        target_profit, stop_loss, add_buy = updater.calculate_optimal_exit_points(
            stock_code, 
            crash_data
        )
        
        print(f"\n💰 최적화 결과:")
        print(f"   목표 익절: +{target_profit:.1f}%")
        print(f"   손절: {stop_loss:.1f}%")
        print(f"   추가 매수: {add_buy:.1f}%")
        
        # 기본값과 비교
        if abs(target_profit - 8.0) > 0.1:
            print(f"   ✨ 기본값(+8%) 대비 {target_profit - 8.0:+.1f}% 차이!")
    
    return True


def test_data_merge():
    """데이터 병합 테스트"""
    print("\n" + "="*70)
    print("📦 TEST 3: 데이터 병합 시뮬레이션")
    print("="*70 + "\n")
    
    updater = RealtimeLearningUpdater()
    
    # 실시간 데이터 파일이 있는지 확인
    realtime_files = list(updater.realtime_dir.glob('crash_*.parquet'))
    
    if realtime_files:
        print(f"📁 실시간 데이터 파일: {len(realtime_files)}개")
        
        # 병합 실행
        df_merged = updater.merge_realtime_to_training_data()
        
        if df_merged is not None:
            print(f"\n✅ 병합 성공!")
            print(f"   최종 데이터: {len(df_merged):,}개")
            return True
    else:
        print("ℹ️  실시간 데이터 없음 (정상)")
        print("   급락 감지 시 자동 생성됩니다.")
    
    return True


def test_full_workflow():
    """전체 워크플로우 테스트"""
    print("\n" + "="*70)
    print("🚀 TEST 4: 전체 워크플로우 (급락 → 최적화 → 매매신호)")
    print("="*70 + "\n")
    
    updater = RealtimeLearningUpdater()
    
    # 1. 학습 데이터에서 최근 급락 종목 선택
    data_path = PROJECT_ROOT / 'data' / 'crash_rebound' / 'all_stocks_3years.parquet'
    
    if not data_path.exists():
        print("❌ 학습 데이터 없음")
        return False
    
    df = pd.read_parquet(data_path)
    
    # 최근 1개월 급락 데이터
    recent_date = df['Date'].max()
    one_month_ago = recent_date - timedelta(days=30)
    
    df_recent_crashes = df[
        (df['Date'] >= one_month_ago) & 
        (df['crash_rate'] <= -10.0)
    ].head(3)
    
    if len(df_recent_crashes) == 0:
        print("ℹ️  최근 급락 종목 없음")
        return True
    
    print(f"📊 최근 1개월 급락 종목: {len(df_recent_crashes)}개\n")
    
    for idx, row in df_recent_crashes.iterrows():
        stock_code = row['stock_code']
        stock_name = row.get('stock_name', stock_code)
        
        print(f"\n{'='*70}")
        print(f"🎯 매매 시뮬레이션: {stock_name}")
        print(f"{'='*70}")
        
        # 최적화
        crash_data = {
            'stock_code': stock_code,
            'Date': row['Date'],
            'Close': row.get('close', row.get('Close', 0)),  # 소문자/대문자 둘 다 지원
            'crash_rate': row['crash_rate']
        }
        
        target_profit, stop_loss, add_buy = updater.calculate_optimal_exit_points(
            stock_code,
            crash_data
        )
        
        # 매매 신호 생성
        entry_price = row.get('close', row.get('Close', 0))
        target_price = entry_price * (1 + target_profit/100)
        stop_price = entry_price * (1 + stop_loss/100)
        add_price = entry_price * (1 + add_buy/100)
        
        print(f"\n💰 매매 계획:")
        print(f"   진입가: {entry_price:,.0f}원")
        print(f"   1차 매수: {entry_price * 0.5:,.0f}원 (50%)")
        print(f"   2차 매수: {add_price:,.0f}원 ({add_buy:.1f}% 하락 시)")
        print(f"   목표가: {target_price:,.0f}원 (+{target_profit:.1f}%)")
        print(f"   손절가: {stop_price:,.0f}원 ({stop_loss:.1f}%)")
        
        # 예상 수익 계산
        investment = 100000  # 10만원 기준
        expected_profit = investment * (target_profit/100)
        
        print(f"\n📊 예상 수익 (10만원 기준):")
        print(f"   목표 달성 시: +{expected_profit:,.0f}원")
        print(f"   손절 시: {investment * (stop_loss/100):,.0f}원")
    
    return True


def main():
    """전체 테스트 실행"""
    print("\n" + "="*70)
    print("🧪 실시간 학습 시스템 전체 테스트")
    print("="*70)
    
    results = []
    
    # Test 1: 급락 감지
    try:
        result = test_crash_detection()
        results.append(("급락 감지", result))
    except Exception as e:
        print(f"❌ 오류: {e}")
        results.append(("급락 감지", False))
    
    # Test 2: 최적화
    try:
        result = test_optimization()
        results.append(("최적화 계산", result))
    except Exception as e:
        print(f"❌ 오류: {e}")
        results.append(("최적화 계산", False))
    
    # Test 3: 데이터 병합
    try:
        result = test_data_merge()
        results.append(("데이터 병합", result))
    except Exception as e:
        print(f"❌ 오류: {e}")
        results.append(("데이터 병합", False))
    
    # Test 4: 전체 워크플로우
    try:
        result = test_full_workflow()
        results.append(("전체 워크플로우", result))
    except Exception as e:
        print(f"❌ 오류: {e}")
        results.append(("전체 워크플로우", False))
    
    # 결과 요약
    print("\n" + "="*70)
    print("📊 테스트 결과 요약")
    print("="*70 + "\n")
    
    for test_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status} - {test_name}")
    
    success_count = sum(1 for _, success in results if success)
    print(f"\n총 {success_count}/{len(results)}개 성공")
    
    if success_count == len(results):
        print("\n🎉 모든 테스트 통과! 시스템 정상 작동!")
    else:
        print("\n⚠️  일부 테스트 실패")


if __name__ == '__main__':
    main()
