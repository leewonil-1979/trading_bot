"""
전체 학습 파이프라인 실행 스크립트
1단계부터 5단계까지 순차적으로 실행합니다.
"""
import sys
from pathlib import Path
import argparse

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from crawler.krx_list.fetch_stocks import KRXStockFetcher
from crawler.naver_minute.bulk_collector import BulkMinuteCollector
from crawler.naver_minute.vi_scanner import VIScanner
from learning.preprocess.preprocess_minute import MinuteDataPreprocessor
from learning.vi_detection.vi_detector import VIDetector
from learning.pattern_analysis.pattern_analyzer import PatternAnalyzer
from learning.backtest.backtester import Backtester
from learning.strategy_generator.strategy_builder import StrategyGenerator
from utils.logger import setup_logger, get_log_filename
from utils.file_utils import list_files, load_json


def stage1_collect_stock_list(logger):
    """1단계: KRX 종목 리스트 수집"""
    logger.info("=" * 60)
    logger.info("1단계: KRX 종목 리스트 수집 시작")
    logger.info("=" * 60)
    
    fetcher = KRXStockFetcher()
    stocks = fetcher.fetch_all_stocks()
    
    fetcher.save_to_csv(stocks, output_path='./data/raw/stock_list.csv')
    fetcher.save_to_json(stocks, output_path='./data/raw/stock_list.json')
    
    logger.info(f"종목 리스트 수집 완료: {len(stocks)}개 종목\n")


def stage2a_scan_vi_stocks(logger, scan_days=30):
    """2-A단계: VI 종목 스캔 (최근 30일)"""
    logger.info("=" * 60)
    logger.info(f"2-A단계: VI 종목 스캔 시작 (최근 {scan_days}일)")
    logger.info("=" * 60)
    
    # 종목 리스트 로드
    stock_data = load_json('./data/raw/stock_list.json')
    stocks = stock_data['stocks']
    
    logger.info(f"스캔 대상: {len(stocks)}개 종목")
    
    # VI 스캔
    scanner = VIScanner()
    vi_stocks = scanner.scan_all_stocks(stocks, scan_days=scan_days, delay=1.0)
    
    # 결과 저장
    scanner.save_vi_stocks(vi_stocks, output_path='./data/raw/vi_stocks.json')
    
    logger.info(f"VI 종목 스캔 완료: {len(vi_stocks)}개 종목 발견\n")
    return vi_stocks


def stage2b_collect_deep_data(logger, timeframe='1', days_back=730):
    """2-B단계: VI 종목 딥 데이터 수집 (2년)"""
    logger.info("=" * 60)
    logger.info(f"2-B단계: VI 종목 딥 데이터 수집 시작 ({timeframe}분봉, {days_back}일)")
    logger.info("=" * 60)
    
    # VI 종목 리스트 로드
    vi_data = load_json('./data/raw/vi_stocks.json')
    vi_stocks = vi_data['stocks']
    
    logger.info(f"수집 대상: {len(vi_stocks)}개 VI 종목")
    
    # 종목 리스트를 BulkCollector 형식으로 변환
    stock_list = [
        {'종목코드': s['stock_code'], '종목명': s['stock_name']} 
        for s in vi_stocks
    ]
    
    # 임시 CSV 생성
    import pandas as pd
    temp_csv = './data/raw/vi_stocks_temp.csv'
    pd.DataFrame(stock_list).to_csv(temp_csv, index=False, encoding='utf-8-sig')
    
    # 딥 수집
    collector = BulkMinuteCollector()
    collector.collect_all(
        timeframe=timeframe,
        days_back=days_back,
        output_dir='./data/raw',
        stock_list_path=temp_csv,
        delay=2.0
    )
    
    # 임시 파일 삭제
    Path(temp_csv).unlink(missing_ok=True)
    
    logger.info("VI 종목 딥 데이터 수집 완료\n")


def stage3_preprocess_data(logger):
    """3단계: 데이터 전처리"""
    logger.info("=" * 60)
    logger.info("3단계: 데이터 전처리 시작")
    logger.info("=" * 60)
    
    preprocessor = MinuteDataPreprocessor()
    
    # 모든 원본 CSV 파일 처리
    raw_files = list_files('./data/raw', pattern='*_1min.csv')
    
    logger.info(f"전처리 대상 파일: {len(raw_files)}개")
    
    for raw_file in raw_files:
        stock_code = raw_file.stem.split('_')[0]
        output_file = f'./data/processed/{stock_code}_1min_processed.csv'
        
        try:
            preprocessor.process_file(str(raw_file), output_file)
            logger.info(f"전처리 완료: {stock_code}")
        except Exception as e:
            logger.error(f"전처리 실패: {stock_code} - {e}")
    
    logger.info("데이터 전처리 완료\n")


def stage4_detect_vi_and_analyze(logger):
    """4단계: VI 탐지 및 패턴 분석"""
    logger.info("=" * 60)
    logger.info("4단계: VI 탐지 및 패턴 분석 시작")
    logger.info("=" * 60)
    
    detector = VIDetector()
    analyzer = PatternAnalyzer()
    
    # 전처리된 파일들 처리
    processed_files = list_files('./data/processed', pattern='*_processed.csv')
    
    logger.info(f"분석 대상 파일: {len(processed_files)}개")
    
    for processed_file in processed_files:
        stock_code = processed_file.stem.split('_')[0]
        
        try:
            # 데이터 로드
            import pandas as pd
            df = pd.read_csv(processed_file, parse_dates=['timestamp'])
            
            # VI 탐지
            down_vi = detector.detect_gap_down_vi(df)
            up_vi = detector.detect_upward_vi(df)
            all_vi = down_vi + up_vi
            
            if len(all_vi) == 0:
                logger.info(f"{stock_code}: VI 이벤트 없음")
                continue
            
            # VI 이벤트 저장
            detector.save_vi_events(all_vi, stock_code)
            
            # 패턴 분석
            analysis_results = analyzer.batch_analyze(df, all_vi)
            analyzer.save_analysis(analysis_results, stock_code)
            
            logger.info(f"{stock_code}: VI {len(all_vi)}개 탐지, 분석 완료")
            
        except Exception as e:
            logger.error(f"{stock_code}: 분석 실패 - {e}")
    
    logger.info("VI 탐지 및 패턴 분석 완료\n")


def stage5_generate_strategy(logger):
    """5단계: 전략 생성"""
    logger.info("=" * 60)
    logger.info("5단계: 전략 생성 시작")
    logger.info("=" * 60)
    
    generator = StrategyGenerator()
    
    # 패턴 분석 결과 파일들 수집
    pattern_files = list_files('./data/patterns', pattern='*_pattern_analysis.json')
    
    logger.info(f"패턴 분석 파일: {len(pattern_files)}개")
    
    # 통합 통계 계산
    integrated_stats = generator.analyze_patterns([str(f) for f in pattern_files])
    
    # 백테스트 결과 로드 (있다면)
    backtest_file = Path('./data/patterns/backtest_results.json')
    backtest_results = {}
    if backtest_file.exists():
        backtest_results = load_json(str(backtest_file))
    
    # 전략 생성
    strategy = generator.generate_strategy(integrated_stats, backtest_results)
    
    # 저장
    generator.save_strategy(strategy, output_path='./config/strategy.json')
    
    logger.info("전략 생성 완료\n")


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description='VI 패턴 학습 파이프라인')
    parser.add_argument('--stage', type=int, default=0, 
                        help='실행할 단계 (0=전체, 1-5=개별 단계)')
    parser.add_argument('--timeframe', type=str, default='1', 
                        help='분봉 단위 (1 or 3)')
    parser.add_argument('--days', type=int, default=730, 
                        help='딥 수집 기간 (일)')
    parser.add_argument('--scan-days', type=int, default=30, 
                        help='VI 스캔 기간 (일)')
    parser.add_argument('--limit', type=int, default=None, 
                        help='종목 수 제한 (테스트용, deprecated)')
    
    args = parser.parse_args()
    
    # 로거 설정
    log_file = get_log_filename('pipeline', './logs')
    logger = setup_logger('Pipeline', log_file)
    
    logger.info("=" * 60)
    logger.info("VI 패턴 학습 파이프라인 시작")
    logger.info("=" * 60)
    
    try:
        if args.stage == 0 or args.stage == 1:
            stage1_collect_stock_list(logger)
        
        if args.stage == 0 or args.stage == 2:
            # 2-A: VI 스캔
            stage2a_scan_vi_stocks(logger, scan_days=args.scan_days)
            # 2-B: 딥 수집
            stage2b_collect_deep_data(logger, timeframe=args.timeframe, days_back=args.days)
        
        if args.stage == 0 or args.stage == 3:
            stage3_preprocess_data(logger)
        
        if args.stage == 0 or args.stage == 4:
            stage4_detect_vi_and_analyze(logger)
        
        if args.stage == 0 or args.stage == 5:
            stage5_generate_strategy(logger)
        
        logger.info("=" * 60)
        logger.info("파이프라인 실행 완료!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"파이프라인 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
