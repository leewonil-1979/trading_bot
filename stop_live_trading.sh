#!/bin/bash
# 자동매매 중지 스크립트

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}⏹️  자동매매 시스템 종료${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# 프로세스 확인
if pgrep -f live_scheduler.py > /dev/null; then
    echo -e "${YELLOW}실행 중인 스케줄러 발견${NC}"
    
    # PID 표시
    PID=$(pgrep -f live_scheduler.py)
    echo "PID: $PID"
    echo ""
    
    # 종료 확인
    read -p "스케줄러를 종료하시겠습니까? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 프로세스 종료
        pkill -f live_scheduler.py
        
        # 종료 확인
        sleep 2
        if pgrep -f live_scheduler.py > /dev/null; then
            echo -e "${RED}❌ 정상 종료 실패, 강제 종료 시도...${NC}"
            pkill -9 -f live_scheduler.py
            sleep 1
        fi
        
        # 최종 확인
        if pgrep -f live_scheduler.py > /dev/null; then
            echo -e "${RED}❌ 종료 실패${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ 스케줄러 종료 완료${NC}"
            echo ""
            echo -e "${YELLOW}📊 마지막 로그 (최근 20줄):${NC}"
            tail -20 logs/live_trading.log 2>/dev/null || echo "로그 파일 없음"
        fi
    else
        echo -e "${YELLOW}종료 취소${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}실행 중인 스케줄러 없음${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 작업 완료${NC}"
echo -e "${GREEN}========================================${NC}"
