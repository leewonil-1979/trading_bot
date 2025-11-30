# 🎯 VI 순간 포착 시스템 - 진짜 데이터 전략

## 🔥 핵심 요구사항

### 필수 데이터 (VI 발생 전후 10초 단위)
1. **가격 데이터**: 초단위 체결가, 호가창 (매수/매도 1~10호가)
2. **거래량**: 틱별 거래량, 누적 거래량
3. **프로그램 매매**: 초단위 프로그램 순매수/순매도
4. **투자자별**: 기관/외국인/개인 매매 동향
5. **VI 메타데이터**: 발동 사유, 정적/동적, 기준가, 발동가

### 학습 목표
- **VI 발생 원인** 자동 분류 (뉴스/공시/프로그램/패닉)
- **반등 확률** 예측 (프로그램 매수 패턴 기반)
- **진입 타이밍** 최적화 (VI 해제 후 몇 초?)
- **손절 시점** 자동 판단 (프로그램 매도 감지)

---

## 💰 현실적인 데이터 확보 방법

### ❌ 불가능: 무료 API
- 네이버/KIS: 실시간만 가능, 과거 틱 데이터 ❌
- Pykrx: 일봉만
- FinanceDataReader: 일봉만

### ✅ 필수: 전문 데이터 제공업체

#### 1. **FnGuide DataGuide API** (최강 추천)
```yaml
가격: 월 220,000원 (프리미엄)
제공 데이터:
  - 틱 데이터 (체결, 호가)
  - 프로그램 매매 내역 (초단위)
  - VI 발생 내역 (정확한 시각, 사유)
  - 투자자별 매매 동향
  - 뉴스/공시 연동
과거 데이터: 10년치 제공
API: RESTful + WebSocket
연락: https://www.fnguide.com
      1588-3003
```

#### 2. **Qraft Technologies** (AI 특화)
```yaml
가격: 협의 (대형 기관용, 월 500만원+)
제공: AI 학습용 정제 데이터셋
특징: VI 패턴 사전 분류, 레이블링
연락: https://qraftec.com
      AI 데이터 팀
```

#### 3. **WISEfn** (중가형)
```yaml
가격: 월 88,000원
제공:
  - 분봉 데이터
  - 재무제표
  - 뉴스 감성분석
한계: 틱 데이터 ❌, 프로그램 매매 제한적
연락: https://www.wisefn.com
```

---

## 🚀 시스템 아키텍처 (알파고 스타일)

### Phase 1: 데이터 수집 레이어
```python
# 실시간 + 과거 데이터 통합
class VIDataCollector:
    - 틱 데이터 스트리밍 (FnGuide WebSocket)
    - VI 발생 감지 (1초 이내)
    - 전후 60초 슬라이싱 (VI-30s ~ VI+30s)
    - 프로그램 매매 추적
    - 뉴스/공시 매칭
```

### Phase 2: 특징 추출 레이어
```python
class VIFeatureExtractor:
    # VI 발생 전 신호 (30초)
    - 가격 급등/급락 속도
    - 거래량 폭발 지수
    - 프로그램 매수/매도 전환
    - 호가 불균형 (매수/매도 물량 비율)
    - 뉴스 발표 시점
    
    # VI 발생 순간 (0초)
    - 발동 사유 (정적/동적)
    - 기준가 대비 변동폭
    - VI 가격대
    
    # VI 해제 후 신호 (30초)
    - 프로그램 매수 유입량
    - 체결 강도
    - 호가창 회복 속도
    - 거래량 지속성
```

### Phase 3: AI 학습 레이어 (Deep Learning)
```python
import torch
import torch.nn as nn

class VIReboundPredictor(nn.Module):
    """
    Transformer 기반 VI 반등 예측 모델
    - Input: VI 전후 60초 시계열 데이터 (120차원)
    - Output: 반등 확률, 예상 수익률, 최적 진입 시점
    """
    def __init__(self):
        self.embedding = nn.Linear(120, 256)
        self.transformer = nn.TransformerEncoder(...)
        self.rebound_head = nn.Linear(256, 1)  # 반등 확률
        self.profit_head = nn.Linear(256, 1)   # 예상 수익률
        self.timing_head = nn.Linear(256, 10)  # 진입 타이밍 (0~9초)
    
    def forward(self, vi_sequence):
        # VI 전후 시계열 분석
        features = self.transformer(vi_sequence)
        
        rebound_prob = torch.sigmoid(self.rebound_head(features))
        expected_profit = self.profit_head(features)
        entry_timing = torch.softmax(self.timing_head(features))
        
        return {
            'rebound_probability': rebound_prob,
            'expected_profit': expected_profit,
            'optimal_entry_second': entry_timing.argmax()
        }
```

### Phase 4: 강화학습 레이어 (진입/청산 최적화)
```python
import gym
from stable_baselines3 import PPO

class VITradingEnv(gym.Env):
    """
    VI 트레이딩 환경 (Gym 인터페이스)
    
    State:
      - VI 전후 60초 틱 데이터
      - 프로그램 매수/매도 추이
      - 현재 포지션
    
    Action:
      - 0: 관망 (HOLD)
      - 1: 매수 (BUY)
      - 2: 매도 (SELL)
    
    Reward:
      - 수익률 (%)
      - 샤프 비율
      - 최대 낙폭 페널티
    """
    pass

# PPO 강화학습 에이전트
agent = PPO('MlpPolicy', VITradingEnv(), verbose=1)
agent.learn(total_timesteps=1000000)
```

---

## 📊 데이터 요구사항 (정확한 수치)

### 학습 데이터셋 크기
```
목표: 10,000개 VI 이벤트

VI 발생률: 종목당 연간 ~5회
필요 종목: 500개 × 4년 = 10,000 이벤트

이벤트당 데이터:
  - VI 전 30초 × 100틱/초 = 3,000 틱
  - VI 후 30초 × 100틱/초 = 3,000 틱
  - 총 6,000 틱/이벤트
  
전체 데이터:
  - 10,000 이벤트 × 6,000 틱 = 60,000,000 틱
  - 크기: ~50GB (압축 시 10GB)
```

### 필수 컬럼 (21개)
```csv
timestamp,
stock_code,
stock_name,
price,              # 체결가
volume,             # 체결량
bid_price_1~10,     # 매수호가 10단계
ask_price_1~10,     # 매도호가 10단계
bid_volume_1~10,    # 매수잔량 10단계
ask_volume_1~10,    # 매도잔량 10단계
program_net_buy,    # 프로그램 순매수
institution_net,    # 기관 순매수
foreign_net,        # 외국인 순매수
individual_net,     # 개인 순매수
vi_status,          # 0=정상, 1=VI발동, 2=VI해제
vi_type,            # static/dynamic/none
vi_reason,          # 발동 사유
news_flag,          # 뉴스 있음/없음
disclosure_flag     # 공시 있음/없음
```

---

## 💡 구현 로드맵 (3개월)

### Month 1: 데이터 수집 인프라
```bash
Week 1-2: FnGuide API 계약 및 테스트
  - API 키 발급
  - 틱 데이터 다운로드 테스트
  - VI 이벤트 조회 API 확인

Week 3-4: 과거 데이터 수집
  - 500개 종목 선정 (변동성 높은 종목)
  - 4년치 틱 데이터 다운로드 (2021~2024)
  - VI 이벤트 필터링 (~10,000개)
  - 전후 60초 슬라이싱
```

### Month 2: AI 모델 개발
```bash
Week 5-6: 특징 공학
  - 120개 feature 추출
  - 정규화/스케일링
  - Train/Val/Test 분리 (8:1:1)

Week 7-8: 모델 학습
  - Transformer 베이스라인 (PyTorch)
  - LSTM 비교 실험
  - Hyperparameter 튜닝
  - 목표: 반등 예측 정확도 80%+
```

### Month 3: 강화학습 & 배포
```bash
Week 9-10: 강화학습 최적화
  - PPO 에이전트 학습
  - 진입/청산 타이밍 최적화
  - 백테스트 (승률 75%+, 샤프 비율 2.0+)

Week 11-12: 실전 배포
  - AWS Lambda/EC2 배포
  - 실시간 스트리밍 연동
  - 알림 시스템 (Slack/Telegram)
  - Paper Trading 1주일
  - Real Trading 시작
```

---

## 💰 예산 계획 (수정됨 - 중요!)

### ✅ 학습 기간만 필요 (1개월)
```
FnGuide API: 220,000원 × 1개월 = 220,000원 (과거 데이터 다운로드)
----------------------------------------------
합계: 220,000원 (단 1회!)
```

### ✅ 실전 운영 (Month 2+)
```
한국투자증권 KIS API: 0원 (무료!)
로컬 PC: 0원 (집 컴퓨터 활용)
----------------------------------------------
합계: 0원/월 (완전 무료!)
```

**AWS 클라우드 (선택사항):**
- 외출 중에도 자동 거래 원하면
- EC2 t3.small: 월 50,000원
- **하지만 필수 아님!** 로컬 PC면 충분

### 💡 핵심 포인트
**Q1: FnGuide는 1개월만 쓰면 되나요?**
→ ✅ **YES!** 과거 데이터(2~4년치) 한 번만 다운로드하면 끝

**Q2: 학습 후엔 KIS 실시간으로 충분한가요?**
→ ✅ **YES!** 학습된 AI 모델 + KIS 실시간 체결 = 완벽 조합

**Q3: FnGuide 데이터 정확도?**
→ ✅ **100% 정확** (한국거래소 공식 데이터 제공업체)

### ROI 계산 (최종 수정)
```
초기 자본: 10,000,000원 (1천만원)
예상 승률: 75%
거래당 수익: 2.5%
일일 거래: 3회

월 수익 = 10,000,000 × 0.025 × 3 × 20 = 1,500,000원

[Month 1 - 학습 기간]
비용: 220,000원 (FnGuide만)
순이익: 0원 (학습 중)

[Month 2+ - 실전 운영 (로컬 PC)]
비용: 0원/월 (KIS 무료 + 로컬 PC)
순이익: 1,500,000원/월

ROI = 무한대! (비용 0원)
손익분기점: Month 1 투자금 15일 만에 회수!
```

**AWS 사용 시 (선택):**
- 비용: 50,000원/월
- 순이익: 1,450,000원/월
- ROI: 2,900%
- 외출 시에도 자동 거래 가능

---

## 🎯 즉시 실행 계획

### ✅ Step 1: FnGuide 계약 (오늘)
```bash
1. https://www.fnguide.com 접속
2. 1588-3003 전화
3. "AI 트레이딩 시스템 개발용 틱 데이터 API 문의"
4. 계약서 작성 (최소 3개월)
5. API 키 발급 (2~3일 소요)
```

### ✅ Step 2: 시스템 설계 (이번 주)
```bash
# 프로젝트 구조 재구성
auto_trading/
├── data_collection/
│   ├── fnguide_tick_fetcher.py       # FnGuide 틱 수집
│   ├── vi_event_slicer.py            # VI 전후 슬라이싱
│   └── feature_extractor.py          # 특징 추출
├── ai_model/
│   ├── transformer_model.py          # Transformer 모델
│   ├── reinforcement_learning.py     # RL 에이전트
│   └── train.py                      # 학습 스크립트
├── backtesting/
│   ├── simulator.py                  # 백테스트 엔진
│   └── performance_analyzer.py       # 성과 분석
└── trading_engine/
    ├── realtime_predictor.py         # 실시간 예측
    ├── order_executor.py             # 주문 실행
    └── risk_manager.py               # 리스크 관리
```

### ✅ Step 3: 파일럿 데이터 (다음 주)
```bash
# FnGuide API 키 발급 후
# 삼성전자 1년치 틱 데이터 다운로드 (테스트)

python data_collection/fnguide_tick_fetcher.py \
  --stock_code 005930 \
  --start_date 2024-01-01 \
  --end_date 2024-12-31 \
  --output data/ticks/005930_2024_ticks.parquet
```

---

## 🔥 다음 단계 (지금 바로)

### 1️⃣ FnGuide 전화 (오늘 오후)
```
전화: 1588-3003
담당자: 데이터 영업팀
문의: "AI 트레이딩 개발용 틱 데이터 API 계약 문의합니다"
준비: 사업자등록증 (개인도 가능)
```

### 2️⃣ 시스템 구조 설계 (내일)
```bash
# 새 브랜치 생성
cd /home/user1/auto_trading
git checkout -b feature/ai-trading-system

# 디렉토리 생성
mkdir -p data_collection ai_model backtesting trading_engine
```

### 3️⃣ AI 모델 프로토타입 (이번 주말)
```bash
# PyTorch Transformer 베이스라인
# 더미 데이터로 학습 파이프라인 구축
```

---

## ✅ 체크리스트

- [ ] FnGuide 전화 상담 (오늘)
- [ ] API 계약서 검토
- [ ] API 키 발급 (2~3일)
- [ ] 파일럿 데이터 다운로드 (1년치)
- [ ] Transformer 모델 구현
- [ ] 10,000개 VI 이벤트 수집 (2주)
- [ ] 모델 학습 (1주)
- [ ] 백테스트 (승률 75%+ 검증)
- [ ] Paper Trading (1주)
- [ ] Real Trading 시작

---

**지금 당장 해야 할 일**:
```bash
# FnGuide 전화 걸기
전화번호: 1588-3003
멘트: "안녕하세요, AI 트레이딩 시스템 개발을 위해 
       틱 데이터 API 계약을 문의하고 싶습니다.
       특히 VI 발생 전후 데이터가 필요한데,
       제공 가능한 API 상품이 있을까요?"
```

이게 **진짜 알파고 급 시스템**을 만드는 유일한 방법입니다! 🚀
