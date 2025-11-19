"""
공통 유틸리티 모듈 - 파일 I/O
"""
import json
import csv
import pandas as pd
from pathlib import Path


def ensure_dir(filepath):
    """
    파일 경로의 디렉토리가 없으면 생성
    
    Args:
        filepath (str): 파일 경로
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


def load_json(filepath):
    """
    JSON 파일 로드
    
    Args:
        filepath (str): JSON 파일 경로
        
    Returns:
        dict: 로드된 데이터
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, filepath, indent=2):
    """
    JSON 파일 저장
    
    Args:
        data (dict): 저장할 데이터
        filepath (str): 저장 경로
        indent (int): 들여쓰기
    """
    ensure_dir(filepath)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, default=str)


def load_csv(filepath, **kwargs):
    """
    CSV 파일 로드
    
    Args:
        filepath (str): CSV 파일 경로
        **kwargs: pandas.read_csv 옵션
        
    Returns:
        pd.DataFrame: 로드된 데이터프레임
    """
    return pd.read_csv(filepath, **kwargs)


def save_csv(df, filepath, **kwargs):
    """
    CSV 파일 저장
    
    Args:
        df (pd.DataFrame): 저장할 데이터프레임
        filepath (str): 저장 경로
        **kwargs: pandas.to_csv 옵션
    """
    ensure_dir(filepath)
    df.to_csv(filepath, encoding='utf-8-sig', **kwargs)


def list_files(directory, pattern='*'):
    """
    디렉토리 내 파일 리스트 반환
    
    Args:
        directory (str): 디렉토리 경로
        pattern (str): 파일 패턴 (예: '*.csv')
        
    Returns:
        list: 파일 경로 리스트
    """
    path = Path(directory)
    return list(path.glob(pattern))
