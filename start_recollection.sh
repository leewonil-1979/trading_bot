#!/bin/bash

# 급락-반등 데이터 재수집 실행 스크립트
# - 투자자 매매 데이터 실제 수집
# - 2~3일 소요
# - 백그라운드 실행

echo "=================================================================="
echo "🚀 급락-반등 데이터 재수집 시작"
echo "=================================================================="
echo ""
echo "⏰ 예상 소요 시간: 2~3일"
echo "📊 대상: 1,842개 종목 × 3년 데이터"
echo "💾 저장 위치: ./data/crash_rebound/"
echo ""
echo "⚠️ 주의사항:"
echo "  - 컴퓨터를 끄지 마세요"
echo "  - 절전 모드 0분 설정 확인"
echo "  - WSL 종료 금지"
echo ""
echo "=================================================================="
echo ""

# Python 가상환경 활성화
source /home/user1/auto_trading/.venv/bin/activate

# 로그 파일 경로
LOG_DIR="/home/user1/auto_trading/data/crash_rebound/logs"
mkdir -p $LOG_DIR
LOG_FILE="$LOG_DIR/recollection_$(date +%Y%m%d_%H%M%S).log"

echo "📝 로그 파일: $LOG_FILE"
echo ""

# 기존 통합 파일 백업
if [ -f "/home/user1/auto_trading/data/crash_rebound/all_stocks_3years.parquet" ]; then
    BACKUP_FILE="/home/user1/auto_trading/data/crash_rebound/all_stocks_3years_backup_$(date +%Y%m%d_%H%M%S).parquet"
    echo "💾 기존 파일 백업: $BACKUP_FILE"
    cp "/home/user1/auto_trading/data/crash_rebound/all_stocks_3years.parquet" "$BACKUP_FILE"
    echo ""
fi

# Python 스크립트 실행
echo "🔄 데이터 수집 시작..."
echo ""

cd /home/user1/auto_trading

# 직접 Python 경로 지정하여 실행
nohup /home/user1/auto_trading/.venv/bin/python data_collection/crash_rebound_collector.py > "$LOG_FILE" 2>&1 &

PID=$!

echo "=================================================================="
echo "✅ 백그라운드 실행 시작!"
echo "=================================================================="
echo ""
echo "프로세스 ID (PID): $PID"
echo "로그 파일: $LOG_FILE"
echo ""
echo "📊 진행 상황 확인:"
echo "  tail -f $LOG_FILE"
echo ""
echo "🛑 중단하려면:"
echo "  kill $PID"
echo ""
echo "📈 진행률 확인:"
echo "  cat data/crash_rebound/collection_progress.json"
echo ""
echo "=================================================================="

# 초기 로그 출력
sleep 3
echo ""
echo "초기 로그:"
echo "------------------------------------------------------------------"
tail -20 "$LOG_FILE"
echo "------------------------------------------------------------------"
