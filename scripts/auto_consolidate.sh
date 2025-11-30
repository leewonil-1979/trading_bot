#!/bin/bash
# 상세 투자자 데이터 수집 완료 후 자동 실행 스크립트

echo "=========================================="
echo "상세 투자자 데이터 수집 완료 대기 중..."
echo "=========================================="

# 완료 대기
while true; do
    # 진행률 확인
    COMPLETED=$(cat data/crash_rebound/detailed_investor_progress.json | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data['completed']))")
    PROGRESS=$(python3 -c "print(f'{$COMPLETED/2193*100:.1f}')")
    
    echo "[$(date +%H:%M:%S)] 진행률: $COMPLETED/2193 ($PROGRESS%)"
    
    # 완료 확인
    if [ "$COMPLETED" -ge 2193 ]; then
        echo ""
        echo "✅ 상세 투자자 데이터 수집 완료!"
        break
    fi
    
    sleep 60  # 1분마다 체크
done

echo ""
echo "=========================================="
echo "1. 통합 파일 생성 시작"
echo "=========================================="

/home/user1/auto_trading/.venv/bin/python data_collection/consolidate_investor_data.py

if [ $? -eq 0 ]; then
    echo "✅ 통합 파일 생성 완료"
else
    echo "❌ 통합 파일 생성 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "2. 상관관계 분석 시작"
echo "=========================================="

/home/user1/auto_trading/.venv/bin/python analysis/investor_correlation_analysis.py

if [ $? -eq 0 ]; then
    echo "✅ 상관관계 분석 완료"
else
    echo "❌ 상관관계 분석 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "🎉 모든 작업 완료!"
echo "=========================================="
echo ""
echo "결과 파일:"
echo "  - data/crash_rebound/all_stocks_3years.parquet"
echo "  - analysis/output/investor_rebound_correlation.png"
echo "  - analysis/output/success_fail_comparison.png"
echo "  - analysis/output/investor_analysis_summary.txt"
echo ""
echo "다음 단계:"
echo "  python ai_model/train_crash_rebound.py  # AI 모델 재학습"
