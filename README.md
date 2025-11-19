# Auto Trading - VI Pattern Learning Project

## 프로젝트 개요
한국 주식 단타 VI(변동성완화장치) 기반 반등 패턴을 자동 학습하고 전략화하는 시스템

## 학습 목표
- **9시 정각 하방 VI 패턴**: Gap Down 후 반등 패턴 학습
- **상방 VI 패턴**: 급등 → VI → 눌림 → 전고점 돌파 패턴 학습
- **목표**: 2년치 전체 종목 데이터로 strategy.json 생성

## 프로젝트 구조
```
auto_trading/
├── data/              # 데이터 저장소
├── crawler/           # 데이터 수집 (KRX, 네이버)
├── learning/          # 학습 파이프라인
├── utils/             # 공통 유틸리티
├── config/            # 설정 파일
├── logs/              # 로그
├── notebooks/         # 분석 노트북
└── pipeline.py        # 메인 실행 파일
```

## 5단계 학습 파이프라인

### 1단계: 종목 리스트 수집
```bash
python pipeline.py --stage 1
```

### 2단계: 분봉 데이터 수집
```bash
# 테스트 (10개 종목, 30일)
python pipeline.py --stage 2 --limit 10 --days 30

# 실전 (전체 종목, 2년)
python pipeline.py --stage 2 --days 730
```

### 3단계: 데이터 전처리
```bash
python pipeline.py --stage 3
```

### 4단계: VI 탐지 및 패턴 분석
```bash
python pipeline.py --stage 4
```

### 5단계: 전략 생성
```bash
python pipeline.py --stage 5
```

### 전체 파이프라인 실행
```bash
# 테스트
python pipeline.py --limit 10 --days 30

# 실전
python pipeline.py --days 730
```

## 필수 패키지 설치
```bash
pip install pandas numpy requests beautifulsoup4 tqdm matplotlib
```

## 출력 파일
- `data/raw/stock_list.json`: 종목 리스트
- `data/raw/*.csv`: 원본 분봉 데이터
- `data/processed/*.csv`: 전처리된 데이터
- `data/vi_events/*.json`: VI 이벤트
- `data/patterns/*.json`: 패턴 분석 결과
- `config/strategy.json`: 최종 전략 파일 ⭐

## 설정 파일
- `config/settings.yaml`: 시스템 설정
- `config/strategy.json`: 매매 전략 (자동 생성)

## 다음 단계
생성된 `strategy.json`을 AWS 서버의 자동매매 엔진에 배포
