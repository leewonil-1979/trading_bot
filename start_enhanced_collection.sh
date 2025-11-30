#!/bin/bash

# 추가 데이터 수집 백그라운드 실행
# 예상 소요시간: 약 1.5~2시간

cd /home/user1/auto_trading

# 로그 파일
LOG_FILE="data/crash_rebound/logs/enhanced_collection_$(date +%Y%m%d_%H%M%S).log"
mkdir -p data/crash_rebound/logs

echo "============================================================"
echo "📊 추가 데이터 수집 시작"
echo "============================================================"
echo "종목: 2,193개"
echo "데이터: 프로그램 매매, 공시, 뉴스 감성"
echo "예상 시간: 1.5~2시간"
echo "로그: $LOG_FILE"
echo "============================================================"
echo ""

# 백그라운드 실행
nohup /home/user1/auto_trading/.venv/bin/python data_collection/enhanced_collector.py > "$LOG_FILE" 2>&1 &

# PID 저장
PID=$!
echo "프로세스 ID (PID): $PID"
echo $PID > data/crash_rebound/enhanced_collector.pid

echo ""
echo "실행 중..."
echo ""
echo "진행 확인:"
echo "  tail -f $LOG_FILE"
echo ""
echo "중단:"
echo "  kill $PID"
echo ""

# 초기 로그 출력
sleep 3
tail -20 "$LOG_FILE"
