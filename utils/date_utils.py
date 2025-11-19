"""
공통 유틸리티 모듈 - 날짜/시간 처리
"""
from datetime import datetime, time, timedelta
import pandas as pd


def is_market_time(dt):
    """
    주식 시장 거래 시간인지 확인
    
    Args:
        dt (datetime): 확인할 시간
        
    Returns:
        bool: 거래 시간 여부
    """
    market_open = time(9, 0)
    market_close = time(15, 30)
    
    current_time = dt.time()
    
    # 주말 제외
    if dt.weekday() >= 5:  # 5=토요일, 6=일요일
        return False
    
    # 거래 시간 확인
    return market_open <= current_time <= market_close


def is_target_timeframe(dt, start=time(9, 0), end=time(10, 15)):
    """
    목표 시간대 (09:00~10:15) 내인지 확인
    
    Args:
        dt (datetime): 확인할 시간
        start (time): 시작 시간
        end (time): 종료 시간
        
    Returns:
        bool: 목표 시간대 여부
    """
    current_time = dt.time()
    return start <= current_time <= end


def get_trading_days(start_date, end_date):
    """
    특정 기간의 거래일 리스트 반환
    
    Args:
        start_date (datetime): 시작일
        end_date (datetime): 종료일
        
    Returns:
        list: 거래일 리스트
    """
    trading_days = []
    current = start_date
    
    while current <= end_date:
        # 주말 제외
        if current.weekday() < 5:
            trading_days.append(current)
        current += timedelta(days=1)
    
    return trading_days


def format_timestamp(dt, fmt='%Y-%m-%d %H:%M:%S'):
    """
    datetime을 문자열로 포맷
    
    Args:
        dt (datetime): datetime 객체
        fmt (str): 포맷 문자열
        
    Returns:
        str: 포맷된 문자열
    """
    return dt.strftime(fmt)


def parse_timestamp(ts_str, fmt='%Y-%m-%d %H:%M:%S'):
    """
    문자열을 datetime으로 파싱
    
    Args:
        ts_str (str): 시간 문자열
        fmt (str): 포맷 문자열
        
    Returns:
        datetime: datetime 객체
    """
    return datetime.strptime(ts_str, fmt)
