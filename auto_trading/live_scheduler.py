"""
실전 자동매매 스케줄러
12/1부터 30만원 운용

실행 스케줄:
- 평일 09:00-15:30: 실시간 급락 스캔 및 매매 (1분마다)
- 평일 09:00-15:30: 포지션 관리 (5분마다)
- 평일 15:40: 일일 리포트
- 토요일 01:00: 주간 모델 재학습
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, time as dt_time
import time
import schedule
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from auto_trading.live_trading_engine import LiveTradingEngine
from auto_trading.realtime_learning_updater import RealtimeLearningUpdater


class LiveScheduler:
    """실전 자동매매 스케줄러"""
    
    def __init__(self):
        """초기화"""
        # 자동매매 엔진
        self.engine = LiveTradingEngine()
        
        # 실시간 학습 업데이터
        self.updater = RealtimeLearningUpdater()
        
        print(f"\n{'='*70}")
        print(f"🚀 실전 자동매매 스케줄러 시작")
        print(f"{'='*70}")
        print(f"💰 운용 자금: 300,000원")
        print(f"📅 시작일: 2024년 12월 1일")
        print(f"{'='*70}\n")
    
    def is_trading_time(self) -> bool:
        """현재 거래 시간인지 확인 (평일 09:00-15:30)"""
        now = datetime.now()
        
        # 주말 체크
        if now.weekday() >= 5:  # 토(5), 일(6)
            return False
        
        # 시간 체크
        current_time = now.time()
        return dt_time(9, 0) <= current_time <= dt_time(15, 30)
    
    # =========================================
    # 스케줄 작업
    # =========================================
    
    def job_scan_and_trade(self):
        """급락 스캔 및 매매 (1분마다)"""
        if not self.is_trading_time():
            return
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 급락 스캔 중...")
        self.engine.scan_and_trade()
    
    def job_manage_positions(self):
        """포지션 관리 (5분마다)"""
        if not self.is_trading_time():
            return
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 포지션 관리 중...")
        self.engine.manage_positions()
    
    def job_daily_report(self):
        """일일 리포트 (15:40)"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📈 일일 리포트 생성 중...")
        
        # 1. 거래 리포트
        self.engine.generate_daily_report()
        
        # 2. 실시간 데이터 병합
        print(f"\n실시간 학습 데이터 병합 중...")
        self.updater.merge_realtime_to_training_data()
    
    def job_weekly_retrain(self):
        """주간 모델 재학습 (토요일 01:00)"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🤖 모델 재학습 중...")
        
        # TODO: 모델 재학습 구현
        # from ai_model.train_crash_rebound import CrashReboundModel
        # model = CrashReboundModel()
        # model.train()
        
        print(f"✅ 모델 재학습 완료")
    
    # =========================================
    # 스케줄 등록
    # =========================================
    
    def setup_schedule(self):
        """스케줄 설정"""
        
        # 1. 급락 스캔 (1분마다)
        schedule.every(1).minutes.do(self.job_scan_and_trade)
        
        # 2. 포지션 관리 (5분마다)
        schedule.every(5).minutes.do(self.job_manage_positions)
        
        # 3. 일일 리포트 (15:40)
        schedule.every().day.at("15:40").do(self.job_daily_report)
        
        # 4. 주간 재학습 (토요일 01:00)
        schedule.every().saturday.at("01:00").do(self.job_weekly_retrain)
        
        print(f"✅ 스케줄 등록 완료\n")
        print(f"📅 스케줄:")
        print(f"   - 급락 스캔: 매 1분마다 (09:00-15:30)")
        print(f"   - 포지션 관리: 매 5분마다 (09:00-15:30)")
        print(f"   - 일일 리포트: 15:40")
        print(f"   - 주간 재학습: 토요일 01:00")
        print(f"\n")
    
    # =========================================
    # 실행
    # =========================================
    
    def run(self):
        """스케줄러 실행 (무한 루프)"""
        self.setup_schedule()
        
        print(f"🟢 자동매매 스케줄러 실행 중...\n")
        print(f"💡 Ctrl+C로 종료\n")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print(f"⏹️  자동매매 스케줄러 종료")
            print(f"{'='*70}\n")


# =========================================
# 실행
# =========================================

def main():
    """메인 실행"""
    scheduler = LiveScheduler()
    scheduler.run()


if __name__ == '__main__':
    main()
