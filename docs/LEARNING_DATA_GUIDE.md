# 📊 학습 데이터 위치 및 구조

## 1. 저장 위치

```
/home/user1/auto_trading/
├── data/
│   ├── crash_rebound/
│   │   ├── all_stocks_3years.parquet  ← 📌 메인 학습 데이터 (219MB)
│   │   ├── 005930_삼성전자.parquet     (개별 종목 파일들)
│   │   ├── 000660_SK하이닉스.parquet
│   │   └── ... (2,193개 종목 × 약 180KB)
│   │
│   └── realtime_crashes/              ← 📌 실시간 수집 데이터 (신규)
│       ├── crash_20251201.parquet
│       ├── crash_20251202.parquet
│       └── archived/                   (병합 완료된 파일들)
│
└── models/
    ├── crash_rebound_model.txt        ← 📌 학습된 AI 모델 (248KB)
    └── feature_importance.csv
```

---

## 2. 데이터 구조

### 📦 `all_stocks_3years.parquet` (메인 학습 데이터)

| 필드 | 설명 | 예시 |
|------|------|------|
| **기본 정보** |
| stock_code | 종목코드 | '005930' |
| stock_name | 종목명 | '삼성전자' |
| Date | 날짜 | 2023-02-22 |
| crash_rate | 급락률 | -15.3 |
| **가격 데이터 (4개)** |
| Open | 시가 | 70000 |
| High | 고가 | 71000 |
| Low | 저가 | 68000 |
| Close | 종가 | 69000 |
| Volume | 거래량 | 15000000 |
| **기술적 지표 (17개)** |
| sma_5 | 5일 이동평균 | 71000 |
| sma_20 | 20일 이동평균 | 73000 |
| rsi | RSI 지표 | 28.5 |
| macd | MACD | -150 |
| macd_signal | MACD 시그널 | -100 |
| macd_diff | MACD 차이 | -50 |
| bb_upper | 볼린저밴드 상단 | 75000 |
| bb_middle | 볼린저밴드 중간 | 72000 |
| bb_lower | 볼린저밴드 하단 | 69000 |
| bb_width | 볼린저밴드 폭 | 8.3 |
| stoch_k | 스토캐스틱 K | 25.0 |
| stoch_d | 스토캐스틱 D | 28.0 |
| atr | 평균 변동폭 | 2500 |
| volume_ma20 | 거래량 20일 평균 | 12000000 |
| volume_spike | 거래량 급증 배수 | 1.8 |
| price_change_5d | 5일 가격 변화율 | -12.5 |
| price_change_20d | 20일 가격 변화율 | -8.3 |
| **투자자 매매 (10개)** |
| institution_net | 기관 순매수 | -50000000 |
| foreign_net | 외국인 순매수 | -30000000 |
| individual_net | 개인 순매수 | 80000000 |
| financial_invest_net | 금융투자 순매수 | -20000000 |
| insurance_net | 보험 순매수 | -5000000 |
| fund_net | 투신 순매수 | -10000000 |
| private_fund_net | 사모 순매수 | -8000000 |
| bank_net | 은행 순매수 | -2000000 |
| other_finance_net | 기타금융 순매수 | -3000000 |
| pension_net | 연기금 순매수 | -2000000 |
| **레이블** |
| rebound_success | 반등 성공 여부 | 1 (True) or 0 (False) |

**총 48개 컬럼** = 5(기본) + 5(가격) + 17(기술적) + 10(투자자) + 1(레이블)

---

## 3. 통계 정보

```
📊 전체 데이터
- 종목 수: 2,193개
- 기간: 2023-02-22 ~ 2025-11-19 (약 3년)
- 총 행: 1,374,025개
- 파일 크기: 219MB
- 급락 이벤트: 11,813개 (0.86%)
- 반등 성공률: 59.2%

🎯 AI 모델 성능
- 알고리즘: LightGBM
- 정확도: 67%
- AUC: 0.729
- 백테스트 승률: 87.9% (확률 60%+ 필터)
- 평균 수익: +8.30%
```

---

## 4. 실시간 학습 업데이트 시스템

### 📅 일정

| 시간 | 작업 | 설명 |
|------|------|------|
| **09:00~15:30** | 실시간 급락 감지 | 1분마다 전종목 스캔 |
| **15:40** | 데이터 병합 | 오늘 급락 → 학습 데이터 추가 |
| **토요일 01:00** | AI 모델 재학습 | 주간 단위 성능 업데이트 |

### 🔄 데이터 플로우

```
1. 장중 급락 감지
   ↓
2. 저장: realtime_crashes/crash_20251201.parquet
   ↓
3. 장마감 후 병합: all_stocks_3years.parquet 업데이트
   ↓
4. 주말 재학습: 모델 성능 개선
   ↓
5. 월요일 적용: 최신 모델로 매매
```

### 💡 핵심 개선 사항

**기존 방식 (고정값)**
```python
익절: +8% (고정)
손절: -5% (고정)
추가매수: -3% (고정)
```

**신규 방식 (종목별 최적화)** ✨
```python
# 삼성전자 급락 시
익절: +12.5%  ← 과거 데이터 분석 (75 percentile)
손절: -5.0%   ← 안전 고정
추가매수: -2.8%  ← 평균 최저점

# SK하이닉스 급락 시  
익절: +15.2%  ← 변동성 높음
손절: -5.0%
추가매수: -4.1%  ← 추가 하락 여지
```

---

## 5. 사용 방법

### 📝 수동 데이터 병합
```bash
cd /home/user1/auto_trading
python auto_trading/realtime_learning_updater.py
```

### 🚀 자동 스케줄러 실행
```bash
cd /home/user1/auto_trading
python auto_trading/auto_trading_scheduler.py
```

### 📊 학습 데이터 확인
```python
import pandas as pd

# 메인 데이터 로드
df = pd.read_parquet('/home/user1/auto_trading/data/crash_rebound/all_stocks_3years.parquet')

print(f"총 데이터: {len(df):,}개")
print(f"종목 수: {df['stock_code'].nunique()}개")
print(f"기간: {df['Date'].min()} ~ {df['Date'].max()}")
print(f"급락 이벤트: {len(df[df['crash_rate'] <= -10]):,}개")
```

---

## 6. 백업 정책

### 자동 백업
- 데이터 병합 시 기존 파일 백업
- 위치: `data/crash_rebound/all_stocks_backup_YYYYMMDD_HHMMSS.parquet`

### 수동 백업 (권장)
```bash
# 주간 백업
cp data/crash_rebound/all_stocks_3years.parquet \
   data/crash_rebound/backup/all_stocks_weekly_$(date +%Y%m%d).parquet
```

---

## 7. 성능 최적화 팁

### 💾 메모리 절약
```python
# Parquet 압축 옵션
df.to_parquet('file.parquet', compression='snappy', index=False)

# 컬럼 타입 최적화
df['Volume'] = df['Volume'].astype('int32')
df['Close'] = df['Close'].astype('float32')
```

### ⚡ 로딩 속도
```python
# 필요한 컬럼만 로드
df = pd.read_parquet('file.parquet', columns=['stock_code', 'Date', 'Close'])

# 날짜 필터링
df = df[df['Date'] >= '2024-01-01']
```

---

## 8. 다음 단계 (12/1 월요일부터)

✅ **실시간 수집 시작**
- 09:00 스케줄러 실행
- 급락 종목 자동 감지
- 매일 15:40 데이터 병합

✅ **AI 모델 자동 업데이트**
- 매주 토요일 새벽 재학습
- 성능 지표 모니터링
- 최적화 파라미터 자동 조정

✅ **종목별 맞춤 전략**
- 급락 시 과거 데이터 분석
- 최적 익절/손절 계산
- 실시간 적용

---

**질문이 있으시면 언제든지 물어보세요! 🚀**
