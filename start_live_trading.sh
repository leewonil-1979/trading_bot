#!/bin/bash
# 실전 자동매매 시작 스크립트 (12/2 월요일 08:50 실행 권장)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 실전 자동매매 시스템 시작${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 프로젝트 디렉토리로 이동
cd /home/user1/auto_trading

# 가상환경 활성화
echo -e "${YELLOW}1. 가상환경 활성화...${NC}"
source learning/trading_bot/bin/activate

# Python 버전 확인
echo -e "${YELLOW}2. Python 버전 확인...${NC}"
python --version

# 필요한 패키지 확인
echo -e "${YELLOW}3. 패키지 확인...${NC}"
python -c "import pandas, numpy, lightgbm, schedule, requests, yaml; print('✅ 모든 패키지 설치됨')"

# 설정 파일 확인
echo -e "${YELLOW}4. 설정 파일 확인...${NC}"
if grep -q "YOUR_APP_KEY" config/settings.yaml; then
    echo -e "${RED}❌ 경고: KIS API 키가 설정되지 않았습니다!${NC}"
    echo -e "${RED}   config/settings.yaml 파일을 수정하세요.${NC}"
    echo ""
    read -p "그래도 계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ API 키 설정 확인됨${NC}"
fi

# mock_mode 확인
if grep -q "mock_mode: true" config/settings.yaml; then
    echo -e "${YELLOW}⚠️  현재 모의투자 모드입니다${NC}"
    MODE="모의투자"
else
    echo -e "${RED}🔴 실전 투자 모드입니다!${NC}"
    MODE="실전투자"
    echo ""
    read -p "실전 투자를 시작하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 로그 디렉토리 생성
echo -e "${YELLOW}5. 로그 디렉토리 생성...${NC}"
mkdir -p logs

# 기존 프로세스 확인
echo -e "${YELLOW}6. 기존 프로세스 확인...${NC}"
if pgrep -f live_scheduler.py > /dev/null; then
    echo -e "${YELLOW}⚠️  이미 실행 중인 스케줄러가 있습니다${NC}"
    read -p "종료하고 새로 시작하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f live_scheduler.py
        sleep 2
        echo -e "${GREEN}✅ 기존 프로세스 종료됨${NC}"
    else
        echo -e "${YELLOW}스크립트를 종료합니다${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✅ 실행 중인 프로세스 없음${NC}"
fi

# 백그라운드 실행
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎯 자동매매 스케줄러 시작${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "모드: ${MODE}"
echo -e "운용 자금: 300,000원"
echo -e "로그 파일: logs/live_trading.log"
echo -e "${GREEN}========================================${NC}"
echo ""

nohup python auto_trading/live_scheduler.py > logs/live_trading.log 2>&1 &
PID=$!

sleep 2

# 프로세스 확인
if ps -p $PID > /dev/null; then
    echo -e "${GREEN}✅ 스케줄러 시작됨 (PID: $PID)${NC}"
    echo ""
    echo -e "${YELLOW}📊 모니터링 명령어:${NC}"
    echo "   tail -f logs/live_trading.log  # 실시간 로그"
    echo "   tail -100 logs/live_trading.log  # 최근 100줄"
    echo ""
    echo -e "${YELLOW}⏹️  종료 명령어:${NC}"
    echo "   pkill -f live_scheduler.py"
    echo ""
    echo -e "${GREEN}🎊 자동매매가 시작되었습니다!${NC}"
    echo ""
    
    # 로그 확인
    read -p "로그를 실시간으로 확인하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tail -f logs/live_trading.log
    fi
else
    echo -e "${RED}❌ 스케줄러 시작 실패${NC}"
    echo "로그를 확인하세요: cat logs/live_trading.log"
    exit 1
fi
