"""
공통 유틸리티 모듈 - 로깅
"""
import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name, log_file=None, level=logging.INFO):
    """
    로거 설정
    
    Args:
        name (str): 로거 이름
        log_file (str): 로그 파일 경로 (None이면 파일 저장 안함)
        level (int): 로그 레벨
        
    Returns:
        logging.Logger: 설정된 로거
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (옵션)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_log_filename(prefix='app', log_dir='../logs'):
    """
    날짜 기반 로그 파일명 생성
    
    Args:
        prefix (str): 파일명 접두사
        log_dir (str): 로그 디렉토리
        
    Returns:
        str: 로그 파일 경로
    """
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"{log_dir}/{prefix}_{timestamp}.log"
