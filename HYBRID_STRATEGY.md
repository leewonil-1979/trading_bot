# 🎯 하이브리드 전략 (과거 데이터 학습 + 실시간 검증)

## 💡 핵심 아이디어: "빠른 학습 → 철저한 검증 → 실전"

### ✅ 왜 이 방법이 최고인가?

```
❌ 실시간만 (무료):
  - 3~6개월 기다려야 함
  - 데이터 부족 위험
  - 학습 시작이 너무 늦음

❌ 과거 데이터만:
  - 과적합 위험
  - 실전과 괴리
  - 검증 부족

✅ 하이브리드 (과거 + 실시간):
  - 1개월 만에 학습 완료! ⭐⭐⭐
  - 과거 10,000개 VI로 충분한 학습
  - 실시간 1개월로 철저한 검증
  - 2개월 후 실전 투입!
```

---

## 📅 타임라인 (총 2개월)

### Month 1: 과거 데이터 학습

```
Week 1 (11/21~11/27):
  1일차: FnGuide 계약 (22만원) ✅
  2~7일차: 과거 10년 데이터 다운로드
    - 목표: 10,000개 VI 이벤트
    - 틱 데이터 (밀리초 단위)
    - 프로그램 매매 (초단위)
    - VI 발동 사유
  → FnGuide 구독 해지 (비용 절감!)

Week 2 (11/28~12/4):
  데이터 전처리
    - VI 전후 60초 추출
    - Feature 생성 (26개)
    - 학습/검증/테스트 분할 (7:2:1)

Week 3-4 (12/5~12/18):
  AI 모델 학습
    - Transformer 훈련
    - 하이퍼파라미터 튜닝
    - 백테스트 (2023~2024 데이터)
    
  목표 성능:
    - 반등 예측 정확도: 75%+
    - 백테스트 승률: 60%+
    - 샤프 비율: 1.5+
```

### Month 2: 실시간 검증

```
Week 5-8 (12/19~1/15):
  실시간 검증 (Paper Trading)
    - KIS WebSocket 실시간 수집 (무료!)
    - AI 모델로 매매 신호 생성
    - 실제 거래 없이 기록만
    
  검증 항목:
    ✓ 과거 데이터와 실시간 괴리
    ✓ 슬리피지/체결 지연
    ✓ VI 감지 정확도
    ✓ 실전 승률 확인
    
  기준:
    - 실시간 승률 ≥ 55%
    - 실전 샤프 비율 ≥ 1.2
    - 최대 낙폭 < -15%
```

### Month 3: 실전 투자

```
Week 9+ (1/16~):
  실전 매매 시작
    - 초기 자본: 1,000만원
    - 1회 투자: 100만원 (10%)
    - 손절: -2%
    - 익절: +3%
    
  운영 환경:
    - 로컬 PC (0원)
    - KIS API (무료)
    - 총 비용: 220,000원 (단 1회!)
```

---

## 💰 비용 구조

### 초기 투자 (Month 1)

```
FnGuide DataGuide Premium: 220,000원 (1개월만)
  ↓
과거 10년 데이터 다운로드
  - 10,000개 VI 이벤트
  - 틱 데이터 (프로그램 매매 초단위)
  - VI 발동 사유
  ↓
구독 해지 (7일 이내 다운로드 완료)
```

### 검증 기간 (Month 2)

```
KIS WebSocket: 0원 (무료 API)
로컬 PC: 0원 (전기세 ~3,000원)
```

### 실전 운영 (Month 3+)

```
KIS API: 0원
로컬 PC: 0원
총 비용: 0원/월 ✅
```

### 총 비용 요약

```
1년 총 비용: 220,000원 (단 1회!)
월 환산: 18,333원

vs 실시간만 (무료):
  - 3개월 지연
  - 학습 데이터 부족 위험
  
vs QuantiWise (11만원/월):
  - 프로그램 매매 10초 단위 (FnGuide 1초 vs)
  - 1년 비용: 132만원 (FnGuide 22만원 vs)

→ FnGuide 1개월 구독이 최고!
```

---

## 🎯 FnGuide vs QuantiWise (과거 데이터)

| 항목 | FnGuide Premium | QuantiWise Pro |
|------|-----------------|----------------|
| **월 비용** | 220,000원 | 220,000원 |
| **과거 틱 데이터** | 10년 ⭐⭐⭐ | 1년 |
| **프로그램 매매** | 초단위 ⭐⭐⭐ | 일봉만 ❌ |
| **VI 발동 사유** | 완벽 ⭐⭐⭐ | 제한적 |
| **VI 이벤트** | 10년 완벽 기록 | 제한적 |
| **다운로드 후** | 영구 보관 ✅ | 영구 보관 ✅ |

**결론: FnGuide 압승!** (프로그램 매매 초단위 때문)

---

## 📊 수집 데이터 상세

### FnGuide에서 받을 데이터

#### 1. 틱 데이터 (10년)
```python
{
  'timestamp': '2024-11-20 09:05:23.123',  # 밀리초
  'stock_code': '005930',
  'price': 71500,
  'volume': 1500,
  'buy_sell': 'buy'
}

목표: 10,000개 VI × 120초 × 평균 10 틱/초 = 12,000,000 틱
용량: ~5GB (압축)
```

#### 2. 프로그램 매매 (초단위) ⭐⭐⭐
```python
{
  'timestamp': '2024-11-20 09:05:23',  # 1초 단위
  'stock_code': '005930',
  'program_buy': 150000000,      # 프로그램 매수 (원)
  'program_sell': 50000000,      # 프로그램 매도
  'program_net': 100000000,      # 순매수 ⭐
  'institution_net': 20000000,   # 기관 순매수
  'foreign_net': -10000000       # 외국인 순매도
}

목표: 10,000개 VI × 120초 = 1,200,000 데이터
용량: ~500MB
```

#### 3. VI 이벤트 메타데이터
```python
{
  'vi_id': 'VI_20241120_005930_001',
  'stock_code': '005930',
  'trigger_time': '2024-11-20 09:05:23.456',
  'release_time': '2024-11-20 09:07:23.456',
  'vi_type': 'dynamic',          # 정적/동적
  'trigger_reason': '대량매도',   # 발동 사유 ⭐⭐⭐
  'base_price': 71000,
  'trigger_price': 65120,        # -8.3%
  'rebound_price': 69500,        # 반등
  'max_loss': -8.3%,
  'max_rebound': +6.7%
}

목표: 10,000개 VI 이벤트
용량: ~50MB
```

#### 4. 호가 데이터 (1초 단위)
```python
{
  'timestamp': '2024-11-20 09:05:23',
  'stock_code': '005930',
  'bid_price_1': 71500,
  'bid_volume_1': 15000,
  ...
  'ask_price_1': 71600,
  'ask_volume_1': 12000,
  ...
}

목표: 10,000 VI × 120초 = 1,200,000 스냅샷
용량: ~2GB
```

### 총 데이터 용량
```
틱 데이터: ~5GB
프로그램 매매: ~500MB
VI 이벤트: ~50MB
호가 데이터: ~2GB
뉴스/공시: ~100MB

총 용량: ~7.65GB ✅ (충분히 관리 가능)
```

---

## 🔌 FnGuide API 사용법

### 1. 계약 및 API 키 발급

```bash
1. 전화: 1588-3003
2. 담당: 데이터 영업팀
3. 요청 사항:
   "DataGuide Premium 1개월 구독하고,
    과거 10년 VI 이벤트 데이터를 다운로드하고 싶습니다.
    - 틱 데이터 (밀리초)
    - 프로그램 매매 (초단위)
    - VI 발동 사유
    1개월 후 해지 예정입니다."

4. 확인:
   ✓ API 키 발급 (즉시)
   ✓ 다운로드 속도 제한 확인
   ✓ 1개월 후 해지 가능 확인
```

### 2. API 엔드포인트

```python
# 베이스 URL
BASE_URL = "https://api.fnguide.com/v1"

# 인증
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# 틱 데이터 조회
GET /market/tick
params = {
    'stock_code': '005930',
    'start_date': '2024-01-01',
    'end_date': '2024-12-31',
    'interval': 'tick'  # 밀리초
}

# 프로그램 매매 조회
GET /market/program_trading
params = {
    'stock_code': '005930',
    'start_date': '2024-01-01',
    'interval': 'second'  # 초단위 ⭐
}

# VI 이벤트 조회
GET /market/vi_events
params = {
    'stock_code': '005930',
    'start_date': '2015-01-01',
    'end_date': '2024-12-31',
    'include_reason': true  # 발동 사유 포함 ⭐
}
```

### 3. 데이터 다운로드 스크립트

```python
# /home/user1/auto_trading/data_collection/fnguide_downloader.py

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class FnGuideDownloader:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.fnguide.com/v1"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def download_vi_events(self, start_date, end_date):
        """VI 이벤트 리스트 다운로드"""
        url = f"{self.base_url}/market/vi_events"
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'include_reason': True,
            'limit': 10000
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        vi_events = response.json()['data']
        
        print(f"✅ VI 이벤트 {len(vi_events)}개 다운로드")
        return vi_events
    
    def download_vi_detail_data(self, vi_event):
        """VI 전후 60초 상세 데이터"""
        stock_code = vi_event['stock_code']
        trigger_time = vi_event['trigger_time']
        
        # 전후 60초 범위
        start = (datetime.fromisoformat(trigger_time) - timedelta(seconds=60))
        end = (datetime.fromisoformat(trigger_time) + timedelta(seconds=60))
        
        # 1. 틱 데이터
        tick_data = self.download_tick_data(
            stock_code, 
            start.isoformat(), 
            end.isoformat()
        )
        
        # 2. 프로그램 매매 (초단위)
        program_data = self.download_program_trading(
            stock_code,
            start.isoformat(),
            end.isoformat()
        )
        
        # 3. 호가 데이터
        orderbook_data = self.download_orderbook(
            stock_code,
            start.isoformat(),
            end.isoformat()
        )
        
        return {
            'vi_event': vi_event,
            'tick_data': tick_data,
            'program_trading': program_data,
            'orderbook': orderbook_data
        }
    
    def batch_download(self, start_date='2015-01-01', end_date='2024-12-31'):
        """10년 데이터 일괄 다운로드"""
        
        print("="*60)
        print("🚀 FnGuide 과거 데이터 다운로드 시작")
        print(f"기간: {start_date} ~ {end_date}")
        print("="*60 + "\n")
        
        # 1. VI 이벤트 리스트
        vi_events = self.download_vi_events(start_date, end_date)
        
        # 2. 각 VI 상세 데이터
        total = len(vi_events)
        for idx, vi_event in enumerate(vi_events, 1):
            print(f"\n[{idx}/{total}] {vi_event['stock_code']} {vi_event['trigger_time']}")
            
            detail_data = self.download_vi_detail_data(vi_event)
            
            # 저장
            self.save_vi_data(detail_data)
            
            # 속도 제한 (초당 5개)
            time.sleep(0.2)
        
        print("\n" + "="*60)
        print("✅ 다운로드 완료!")
        print(f"총 VI 이벤트: {total}개")
        print("="*60)
```

---

## 📈 학습 및 검증 프로세스

### Phase 1: 과거 데이터 학습 (Week 1-4)

```python
# Week 1: 데이터 수집
python data_collection/fnguide_downloader.py \
  --start_date 2015-01-01 \
  --end_date 2024-12-31 \
  --output ./data/fnguide

# Week 2: 전처리
python preprocessing/prepare_vi_dataset.py \
  --input ./data/fnguide \
  --output ./data/processed

# Week 3-4: AI 학습
python ai_model/train.py \
  --data ./data/processed \
  --epochs 100 \
  --batch_size 32

# 백테스트
python backtesting/backtest.py \
  --model ./models/vi_transformer_best.pth \
  --data ./data/processed/test \
  --period 2023-01-01,2024-12-31
```

**목표 성능 (백테스트)**
```
반등 예측 정확도: 75%+
백테스트 승률: 60%+
월 수익률: 5%+
샤프 비율: 1.5+
최대 낙폭: -15% 이내
```

### Phase 2: 실시간 검증 (Week 5-8)

```python
# Paper Trading (모의 거래)
python trading_engine/paper_trading.py \
  --model ./models/vi_transformer_best.pth \
  --capital 10000000 \
  --position_size 0.1

# 매일 장 시간 실행
# - KIS WebSocket으로 실시간 데이터 수집
# - AI 모델로 매매 신호 생성
# - 실제 거래 없이 기록만
```

**검증 항목**
```
1. 과거 vs 실시간 괴리
   - 백테스트 승률: 60%
   - 실시간 승률: ≥ 55% 필요

2. 슬리피지/체결 지연
   - 예상 진입가: 70,000원
   - 실제 체결가: 70,100원 (0.14% 슬리피지)

3. VI 감지 정확도
   - 자동 감지 성공률: ≥ 95%

4. 실전 샤프 비율
   - 목표: ≥ 1.2
```

**검증 통과 기준**
```
✓ 실시간 승률 ≥ 55%
✓ 실전 샤프 비율 ≥ 1.2
✓ 최대 낙폭 < -15%
✓ VI 감지 성공률 ≥ 95%
✓ 평균 슬리피지 < 0.3%
```

### Phase 3: 실전 투자 (Week 9+)

```python
# 실전 매매
python trading_engine/realtime_trader.py \
  --model ./models/vi_transformer_best.pth \
  --capital 10000000 \
  --position_size 0.1 \
  --stop_loss -0.02 \
  --take_profit 0.03

# 리스크 관리
# - 1회 투자: 100만원 (10%)
# - 손절: -2%
# - 익절: +3%
# - 일일 최대 손실: -5% (500만원)
```

---

## 🎯 예상 성과

### 백테스트 (과거 데이터)

```
기간: 2023-01-01 ~ 2024-12-31 (2년)
초기 자본: 10,000,000원

예상 성과:
  총 거래: 1,200회 (VI 발생)
  승률: 60%
  평균 수익: +1.8%
  평균 손실: -1.2%
  
최종 자본: 13,500,000원
총 수익률: +35%
연 수익률: 17.5%
샤프 비율: 1.8
최대 낙폭: -12%
```

### 실시간 검증 (1개월)

```
기간: 2024-12-19 ~ 2025-01-15 (1개월)
초기 자본: 10,000,000원

예상 성과:
  총 거래: 40~60회
  승률: 55~58% (약간 하락 예상)
  평균 수익: +1.5%
  평균 손실: -1.3%
  
월 수익: +300,000원 ~ +500,000원
월 수익률: +3~5%
```

### 실전 투자 (1년)

```
초기 자본: 10,000,000원

보수적 시나리오 (승률 55%):
  월 수익률: 3%
  연 수익률: 36%
  연 수익: 3,600,000원

중립적 시나리오 (승률 58%):
  월 수익률: 5%
  연 수익률: 60%
  연 수익: 6,000,000원

낙관적 시나리오 (승률 60%):
  월 수익률: 7%
  연 수익률: 84%
  연 수익: 8,400,000원
```

---

## ✅ 실행 체크리스트

### 이번 주 (11/21~11/27)

- [ ] **FnGuide 계약** (1588-3003)
  - DataGuide Premium 1개월
  - API 키 발급
  - 다운로드 속도 확인
  
- [ ] **다운로드 스크립트 작성**
  - fnguide_downloader.py
  - VI 이벤트 10,000개 목표
  
- [ ] **데이터 다운로드 시작**
  - 2015~2024 (10년)
  - 목표: 7일 이내 완료

### 다음 주 (11/28~12/4)

- [ ] **FnGuide 구독 해지** ✅
- [ ] **데이터 전처리**
  - VI 전후 60초 추출
  - Feature 생성
  - 학습/검증/테스트 분할

### 12월 1~2주 (12/5~12/18)

- [ ] **AI 모델 학습**
  - Transformer 훈련
  - 하이퍼파라미터 튜닝
  - 백테스트

### 12월 3주~1월 중순 (12/19~1/15)

- [ ] **실시간 검증 (Paper Trading)**
  - KIS WebSocket 수집
  - 모의 거래 40~60회
  - 성과 분석

### 1월 중순 이후 (1/16~)

- [ ] **실전 투자 시작**
  - 초기 자본: 1,000만원
  - 리스크 관리 철저

---

## 💡 핵심 정리

### ✅ 왜 하이브리드인가?

```
과거 데이터 (FnGuide):
  - 10,000개 VI로 충분한 학습
  - 1개월 만에 AI 완성
  - 비용: 22만원 (단 1회)

실시간 검증 (KIS):
  - 실전 괴리 확인
  - 슬리피지 측정
  - 비용: 0원

→ 2개월 후 실전 투입!
→ 총 비용: 22만원
→ 안정적 + 빠름
```

**지금 바로 FnGuide 전화하세요!** 📞 1588-3003
