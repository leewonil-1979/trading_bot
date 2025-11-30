# 📊 한국 주식 틱/분봉 데이터 확보 가이드

## ✅ 현재 상황
- **문제**: FinanceDataReader는 일봉만 제공 (분봉 ❌)
- **필요**: VI 정확한 탐지를 위한 1분봉/틱 데이터
- **목적**: 9시 VI 반등 패턴 학습, 프로그램 매수 감지

---

## 🎯 추천 솔루션: 한국투자증권 KIS API (무료)

### ✅ 장점
- **무료** (계좌 개설만 필요)
- **실시간 웹소켓** 체결 스트리밍
- **과거 일봉 데이터** 제공
- **안정적** 공식 API

### ❌ 단점
- **과거 분봉 ❌** (일봉만 제공)
- **실시간만 가능** (장 시간 09:00~15:30)
- **웹소켓 구현 필요**

### 📌 사용 방법

#### 1. API 키 발급
```bash
1. https://apiportal.koreainvestment.com 접속
2. 회원가입 (한투 계좌 필요)
3. [서비스 신청] → [국내주식시세] 선택
4. 앱 등록 → APP_KEY, APP_SECRET 복사
```

#### 2. 실시간 데이터 수집 (장 시간)
```bash
cd /home/user1/auto_trading
source learning/trading_bot/bin/activate

# 웹소켓 라이브러리 설치
pip install websocket-client

# 실시간 분봉 수집 (60분)
python crawler/kis_api/kis_realtime_websocket.py
```

#### 3. 매일 장 시간에 수집
```bash
# cron 설정 (평일 09:00~15:30 자동 수집)
crontab -e

# 매일 09:00 시작 (6시간 30분 수집)
0 9 * * 1-5 cd /home/user1/auto_trading && source learning/trading_bot/bin/activate && python crawler/kis_api/kis_realtime_websocket.py --duration 390 > logs/kis_realtime_$(date +\%Y\%m\%d).log 2>&1
```

---

## 🆓 다른 무료 옵션

### 2. 네이버 금융 API (불안정)
**상태**: ❌ 장 마감 후 데이터 없음
```python
# crawler/naver_minute/fetch_minute_data.py
# 장 시간(09:00~15:30)에만 작동
# 과거 데이터 제한적
```

### 3. Pykrx 라이브러리
```bash
pip install pykrx
```

```python
from pykrx import stock
from datetime import datetime

# 일봉 (무료)
df = stock.get_market_ohlcv("20240101", "20241119", "005930")
print(df)

# 분봉 ❌ 미제공
```

---

## 💰 유료 옵션 (정확도 95%+)

### 1. QuantDataManager (추천)
- **가격**: 월 55,000원
- **제공**: 전체 종목 틱 데이터, 과거 10년
- **API**: RESTful
- **사이트**: https://www.quantdatamanager.com (확인 필요)

### 2. WISEfn 데이터
- **가격**: 월 88,000원
- **제공**: 분봉 + 재무제표 + 뉴스
- **사이트**: https://www.wisefn.com

### 3. FnGuide DataGuide
- **가격**: 월 220,000원 (프리미엄)
- **제공**: 틱 데이터 + 프로그램 매매 내역
- **사이트**: https://www.fnguide.com

---

## 🔥 현실적인 추천 전략

### ✅ **Phase 1: 무료 KIS 실시간 수집 (1개월)**
```bash
# 목표: 1개월간 매일 장 시간 실시간 수집
# 결과: ~20일 × 375분 = 7,500분봉/종목
# 비용: 0원
```

**장점**:
- 비용 절감
- VI 패턴 검증 가능
- 프로그램 매수 감지 가능

**단점**:
- 1개월 데이터만 (2년 불가)
- 매일 수동 관리 필요

### ⭐ **Phase 2: 검증 후 유료 전환**
```bash
# Phase 1에서 승률 70% 확인되면 → QuantDataManager 구독
# 2년치 과거 데이터 다운로드
# 재학습 → 승률 85%+ 목표
```

---

## 📝 현재 프로젝트 적용 방법

### ✅ 즉시 실행 가능: KIS 실시간 수집

#### Step 1: 웹소켓 설치
```bash
cd /home/user1/auto_trading
source learning/trading_bot/bin/activate
pip install websocket-client
```

#### Step 2: API 키 설정
```python
# crawler/kis_api/kis_realtime_websocket.py
# 이미 입력된 키 사용
APP_KEY = "PSSTDXlBU05I5MWOWk9tzEcsPNdqQ8HejPax"
APP_SECRET = "aOMY7LAayo5v0/BU+3SdMF03bmhu7pEqI7yrZK0N5CxblbVNchK+Y8Q4rt8qbhTe8HpoFwzPiOvCLfJAJSVfeLgo7qC3mTacLix9XmwfbYbqYWFihBJYMuHhjpEH4tOZvq77ozfGkpRGrwJzm7/UaXWR6Z/PXKYSWLToRN+5cCt6u1sNdv4="
```

#### Step 3: 장 시간 실시간 수집 (내일 아침)
```bash
# 2024년 11월 20일 (수) 09:00 실행
cd /home/user1/auto_trading
source learning/trading_bot/bin/activate

# VI 관심 종목 실시간 수집
python -c "
from crawler.kis_api.kis_realtime_websocket import KISRealtimeCollector

# VI 의심 종목 (Stage 2 결과에서 가져옴)
vi_stocks = ['329180', '402340', '000240']  # 상위 3개

collector = KISRealtimeCollector(
    'PSSTDXlBU05I5MWOWk9tzEcsPNdqQ8HejPax',
    'aOMY7LAayo5v0/BU+3SdMF03bmhu7pEqI7yrZK0N5CxblbVNchK+Y8Q4rt8qbhTe8HpoFwzPiOvCLfJAJSVfeLgo7qC3mTacLix9XmwfbYbqYWFihBJYMuHhjpEH4tOZvq77ozfGkpRGrwJzm7/UaXWR6Z/PXKYSWLToRN+5cCt6u1sNdv4='
)

# 09:00~15:30 (6.5시간 = 390분) 수집
collector.collect_1min_candles(vi_stocks, duration_minutes=390)
"
```

#### Step 4: 1개월 수집 후 학습
```bash
# 20일치 데이터 확보 후
# data/realtime/*.csv → 분봉 데이터
# Stage 3~5 재실행
python pipeline.py --stage 3
python pipeline.py --stage 4
python pipeline.py --stage 5
```

---

## 🎯 최종 권장 로드맵

### Week 1-4: 무료 KIS 실시간 수집
- 매일 장 시간 실시간 데이터 수집
- VI 종목 20~30개 집중 모니터링
- 프로그램 매수 패턴 검증

### Week 5: 1차 백테스트
- 1개월 데이터로 전략 학습
- 승률 검증 (목표 65%+)
- 프로그램 매수 신호 유효성 확인

### Week 6+: 유료 전환 여부 결정
**IF 승률 70%+**:
→ QuantDataManager 구독 (월 55,000원)
→ 2년 과거 데이터 다운로드
→ 재학습 → 승률 85%+ 목표
→ AWS 배포

**IF 승률 60% 이하**:
→ 전략 재설계
→ 추가 무료 수집 지속

---

## 🚀 지금 바로 실행

```bash
# 1. 웹소켓 라이브러리 설치
cd /home/user1/auto_trading
source learning/trading_bot/bin/activate
pip install websocket-client

# 2. 내일 (11/20 수요일) 09:00에 실행할 준비
echo "
#!/bin/bash
cd /home/user1/auto_trading
source learning/trading_bot/bin/activate
python crawler/kis_api/kis_realtime_websocket.py
" > run_realtime.sh
chmod +x run_realtime.sh

# 3. 09:00에 실행
# ./run_realtime.sh
```

---

## ✅ 체크리스트

- [x] KIS API 키 발급 완료
- [ ] websocket-client 설치
- [ ] 내일 아침 09:00 실시간 수집 실행
- [ ] 1주일 데이터 확보 (최소 5일)
- [ ] 분봉 데이터로 Stage 3~5 재실행
- [ ] 승률 검증 후 유료 전환 결정

---

**다음 액션**:
```bash
pip install websocket-client
```
그리고 내일 아침 장 시작 전(08:55) 실행 준비!
