# 🎯 2단계 샘플링 파이프라인 구현 완료

## ✅ 완료된 수정사항

### 1. VIScanner 모듈 생성 (`crawler/naver_minute/vi_scanner.py`)
- **목적**: 최근 30일 데이터로 VI 발생 종목 빠르게 스캔
- **주요 기능**:
  - `quick_scan()`: 개별 종목 VI 패턴 탐지
  - `scan_all_stocks()`: 전체 종목 일괄 스캔
  - `save_vi_stocks()`: VI 종목 리스트 저장 (JSON)

### 2. Pipeline 2단계 분리 (`pipeline.py`)
**기존**: `stage2_collect_minute_data()` → 전체 종목 2년치 수집

**신규**:
- `stage2a_scan_vi_stocks()`: 전체 종목 30일 스캔 → VI 종목 추출
- `stage2b_collect_deep_data()`: VI 종목만 2년치 딥 수집

### 3. BulkMinuteCollector 개선 (`crawler/naver_minute/bulk_collector.py`)
- `stock_list_path` 파라미터 추가 → 커스텀 종목 리스트 지원
- JSON/CSV 자동 감지 기능 추가

### 4. 명령줄 옵션 추가
```bash
python pipeline.py --stage 2 --scan-days 30 --days 730
```
- `--scan-days`: VI 스캔 기간 (기본 30일)
- `--days`: 딥 수집 기간 (기본 730일)

## 📊 예상 효과

### 기존 방식 (전체 수집)
- 종목 수: 4,203개
- 기간: 2년
- 예상 소요 시간: **100~200시간** (4~8일)
- 데이터 크기: ~500GB

### 새 방식 (2단계 샘플링)
**Stage 2-A (스캔)**:
- 종목 수: 4,203개
- 기간: 30일
- 예상 소요 시간: 2~3시간
- VI 종목 발견: 200~400개 (추정 5~10%)

**Stage 2-B (딥 수집)**:
- 종목 수: 200~400개 (VI 발견 종목만)
- 기간: 2년
- 예상 소요 시간: 2~3시간

**총 소요 시간**: **4~6시간** (vs. 기존 100~200시간)
**효율 개선**: **95% 시간 절약** ⚡

## ⚠️ 현재 이슈

### 네이버 API 데이터 부족
```
[005930] 데이터 수집 오류: Expecting value: line 2 column 3
```
- **원인**: 장 마감 후 또는 주말이라 실시간 분봉 데이터 없음
- **해결**: 장 시간(09:00~15:30)에 실행 필요
- **대안**: 다른 데이터 소스 검토 (KRX, KIS API 등)

## 🚀 실행 방법

### 전체 파이프라인 (0단계 = 전체)
```bash
cd /home/user1/auto_trading
python pipeline.py --stage 0
```

### 단계별 실행
```bash
# 1단계: 종목 리스트 수집
python pipeline.py --stage 1

# 2단계: VI 스캔 + 딥 수집
python pipeline.py --stage 2 --scan-days 30 --days 730

# 2-A만: VI 스캔
python -c "
from pipeline import stage2a_scan_vi_stocks
from utils.logger import setup_logger
logger = setup_logger('test', './logs/test.log')
stage2a_scan_vi_stocks(logger, scan_days=30)
"

# 3단계: 전처리
python pipeline.py --stage 3

# 4단계: VI 탐지 및 분석
python pipeline.py --stage 4

# 5단계: 전략 생성
python pipeline.py --stage 5
```

## 📁 출력 파일

```
data/raw/
  ├── stock_list.json          # 전체 종목 리스트 (4,203개)
  ├── vi_stocks.json           # VI 종목 리스트 (200~400개)
  ├── 005930_1min.csv          # 개별 종목 분봉 데이터
  └── ...
```

## 🔧 다음 단계

1. **장 시간에 실제 데이터 수집 테스트**
   ```bash
   # 소규모 테스트 (10개 종목, 7일)
   python -c "
   from crawler.naver_minute.vi_scanner import VIScanner
   from utils.file_utils import load_json
   data = load_json('./data/raw/stock_list.json')
   scanner = VIScanner()
   results = scanner.scan_all_stocks(data['stocks'][:10], scan_days=7)
   scanner.save_vi_stocks(results)
   "
   ```

2. **API 대안 검토** (네이버가 안정적이지 않을 경우)
   - KRX API
   - 한국투자증권 KIS API
   - FinanceDataReader 라이브러리

3. **Stage 3~5 실행 준비**
   - 실제 VI 데이터 확보 후
   - 전처리 → 탐지 → 전략 생성

## 📝 변경 파일 목록

1. ✅ `crawler/naver_minute/vi_scanner.py` (신규)
2. ✅ `crawler/naver_minute/bulk_collector.py` (수정)
3. ✅ `pipeline.py` (수정)
4. ✅ `TEST_PIPELINE.md` (신규)
