#!/usr/bin/env python
"""
소규모 테스트: 100개 종목으로 2단계 파이프라인 실행
"""
import sys
sys.path.insert(0, '.')

from utils.logger import setup_logger, get_log_filename
from utils.file_utils import load_json
from crawler.naver_minute.vi_scanner import VIScanner
from crawler.naver_minute.bulk_collector import BulkMinuteCollector
import pandas as pd
from pathlib import Path

# 로거 설정
log_file = get_log_filename('test_stage2', './logs')
logger = setup_logger('TestStage2', log_file)

logger.info("=" * 60)
logger.info("Stage 2 소규모 테스트 시작 (100개 종목)")
logger.info("=" * 60)

# 1. 종목 리스트 로드
stock_data = load_json('./data/raw/stock_list.json')
test_stocks = stock_data['stocks'][:100]  # 100개만

logger.info(f"테스트 대상: {len(test_stocks)}개 종목")

# 2-A. VI 스캔 (30일)
logger.info("\n[2-A] VI 스캔 시작...")
scanner = VIScanner()
vi_stocks = scanner.scan_all_stocks(test_stocks, scan_days=30, delay=0.3)
scanner.save_vi_stocks(vi_stocks, output_path='./data/raw/vi_stocks.json')

logger.info(f"✅ VI 스캔 완료: {len(vi_stocks)}개 종목 발견")
logger.info(f"VI 발견율: {len(vi_stocks)/len(test_stocks)*100:.1f}%")

# 상위 10개 출력
if vi_stocks:
    logger.info("\n[발견된 VI 종목 Top 10]")
    sorted_vi = sorted(vi_stocks, key=lambda x: x['vi_count'], reverse=True)[:10]
    for v in sorted_vi:
        logger.info(f"  {v['stock_code']} {v['stock_name']}: VI 점수 {v['vi_count']}")

# 2-B. VI 종목만 딥 수집 (2년) - 상위 10개만 테스트
logger.info(f"\n[2-B] 딥 데이터 수집 시작 (상위 10개만)...")
top_vi_stocks = sorted(vi_stocks, key=lambda x: x['vi_count'], reverse=True)[:10]

stock_list = [
    {'종목코드': str(s['stock_code']).zfill(6), '종목명': s['stock_name']} 
    for s in top_vi_stocks
]

logger.info(f"딥 수집 대상: {stock_list[:3]}")

temp_csv = './data/raw/test_vi_stocks.csv'
df_temp = pd.DataFrame(stock_list)
df_temp['종목코드'] = df_temp['종목코드'].astype(str)
df_temp.to_csv(temp_csv, index=False, encoding='utf-8-sig')

collector = BulkMinuteCollector()
collector.collect_all(
    timeframe='1',
    days_back=730,  # 2년
    output_dir='./data/raw',
    stock_list_path=temp_csv,
    delay=0.5
)

Path(temp_csv).unlink(missing_ok=True)

logger.info("=" * 60)
logger.info("✅ Stage 2 테스트 완료!")
logger.info("=" * 60)
