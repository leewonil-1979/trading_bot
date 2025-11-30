"""
자동매매 스케줄러

일정:
- 09:00~15:30: 실시간 급락 감지 및 매매
- 15:40: 일별 데이터 병합
- 주말 토요일 01:00: AI 모델 재학습
"""

import schedule
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 프로젝트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from auto_trading.realtime_learning_updater import RealtimeLearningUpdater
from ai_model.train_crash_rebound import CrashReboundModel


class AutoTradingScheduler:
    """자동매매 스케줄 관리"""
    
    def __init__(self):
        self.updater = RealtimeLearningUpdater()
        self.model = CrashReboundModel()
        
        self.is_trading_hours = False
        self.today_crashes = []
        
    def check_trading_hours(self) -> bool:
        """장 운영 시간 확인"""
        now = datetime.now()
        
        # 주말 체크
        if now.weekday() >= 5:  # 토,일
            return False
        
        # 시간 체크 (09:00 ~ 15:30)
        current_time = now.time()
        market_open = datetime.strptime('09:00', '%H:%M').time()
        market_close = datetime.strptime('15:30', '%H:%M').time()
        
        return market_open <= current_time <= market_close
    
    # =========================================
    # 1. 실시간 급락 모니터링 (장중)
    # =========================================
    
    def scan_realtime_crashes(self):
        """실시간 급락 스캔 (1분마다)"""
        if not self.check_trading_hours():
            return
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 급락 스캔 중...")
        
        # TODO: 전체 종목 또는 관심 종목 리스트
        # 실전에서는 WebSocket으로 실시간 체결 감지
        watchlist = self._get_watchlist()
        
        for stock_code, stock_name in watchlist:
            crash = self.updater.detect_realtime_crash(stock_code, stock_name)
            
            if crash:
                # 급락 데이터 저장
                self.updater.save_daily_crash(crash)
                self.today_crashes.append(crash)
                
                # AI 예측 + 최적화
                self._process_crash_signal(crash)
    
    def _get_watchlist(self) -> list:
        """모니터링 대상 종목 리스트"""
        # 임시: 주요 종목만
        # 실전: 전체 종목 또는 거래량/변동성 기준 필터
        return [
            ('005930', '삼성전자'),
            ('000660', 'SK하이닉스'),
            ('035420', 'NAVER'),
            ('035720', '카카오'),
            ('051910', 'LG화학'),
            ('006400', '삼성SDI'),
            ('207940', '삼성바이오로직스'),
            ('005380', '현대차'),
            ('105560', 'KB금융'),
        ]
    
    def _process_crash_signal(self, crash: dict):
        """급락 신호 처리 → AI 예측 → 매매 결정"""
        stock_code = crash['stock_code']
        stock_name = crash['stock_name']
        
        print(f"\n{'='*70}")
        print(f"🚨 급락 신호: [{stock_name}] {crash['crash_rate']:.1f}%")
        print(f"{'='*70}")
        
        # 1. AI 모델 예측
        # TODO: 실제 구현
        # probability = self.model.predict_single(crash)
        probability = 0.75  # 임시
        
        print(f"🤖 AI 예측 확률: {probability*100:.1f}%")
        
        # 2. 확률 60% 이상만 진행
        if probability < 0.6:
            print("⏭️  확률 낮음 → 패스")
            return
        
        # 3. 최적 익절/손절 계산
        target_profit, stop_loss, add_buy_point = \
            self.updater.calculate_optimal_exit_points(stock_code, crash)
        
        # 4. 매매 신호 생성
        trade_signal = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'action': 'BUY',
            'price': crash['Close'],
            'ai_probability': probability,
            'target_profit': target_profit,
            'stop_loss': stop_loss,
            'additional_buy_point': add_buy_point,
            'timestamp': datetime.now()
        }
        
        print(f"\n💰 매매 신호:")
        print(f"   진입가: {crash['Close']:,.0f}원")
        print(f"   목표 익절: +{target_profit:.1f}%")
        print(f"   손절: {stop_loss:.1f}%")
        print(f"   추가 매수: {add_buy_point:.1f}%")
        
        # 5. 매매 실행 (실전)
        # TODO: KIS API 주문
        # self.execute_trade(trade_signal)
        
        # 6. Telegram 알림
        # TODO: 텔레그램 봇
        # self.send_telegram_alert(trade_signal)
    
    # =========================================
    # 2. 일별 데이터 병합 (장마감 후)
    # =========================================
    
    def daily_data_merge(self):
        """매일 15:40 실행"""
        print(f"\n{'='*70}")
        print(f"⏰ 일별 데이터 병합 시작 [{datetime.now()}]")
        print(f"{'='*70}\n")
        
        # 실시간 데이터 → 학습 데이터 병합
        self.updater.merge_realtime_to_training_data()
        
        # 오늘 급락 통계
        print(f"\n📊 오늘 급락 종목: {len(self.today_crashes)}개")
        self.today_crashes = []  # 초기화
    
    # =========================================
    # 3. 주간 모델 재학습 (주말)
    # =========================================
    
    def weekly_model_retrain(self):
        """토요일 새벽 1시 실행"""
        print(f"\n{'='*70}")
        print(f"🤖 AI 모델 재학습 시작 [{datetime.now()}]")
        print(f"{'='*70}\n")
        
        # 모델 재학습
        data_path = PROJECT_ROOT / 'data' / 'crash_rebound' / 'all_stocks_3years.parquet'
        
        if not data_path.exists():
            print("❌ 학습 데이터 없음")
            return
        
        try:
            # 데이터 로드
            import pandas as pd
            df = pd.read_parquet(data_path)
            
            print(f"📊 학습 데이터: {len(df):,}개")
            
            # 모델 학습
            # TODO: train 메서드 구현 필요 (현재 스킵)
            # self.model.train(df)
            
            print("\n✅ 모델 재학습 완료 (스킵)!")
            
        except Exception as e:
            print(f"❌ 재학습 오류: {e}")
    
    # =========================================
    # 4. 스케줄 등록
    # =========================================
    
    def setup_schedules(self):
        """스케줄 등록"""
        print("\n" + "="*70)
        print("⏰ 자동매매 스케줄러 시작")
        print("="*70 + "\n")
        
        # 1분마다: 실시간 급락 스캔 (장중만)
        schedule.every(1).minutes.do(self.scan_realtime_crashes)
        
        # 매일 15:40: 데이터 병합
        schedule.every().day.at("15:40").do(self.daily_data_merge)
        
        # 토요일 새벽 1시: 모델 재학습
        schedule.every().saturday.at("01:00").do(self.weekly_model_retrain)
        
        print("✅ 스케줄 등록 완료:")
        print("   - 실시간 급락 스캔: 1분마다 (09:00~15:30)")
        print("   - 데이터 병합: 매일 15:40")
        print("   - 모델 재학습: 토요일 01:00")
        print()
    
    def run(self):
        """스케줄러 실행"""
        self.setup_schedules()
        
        print("🚀 스케줄러 가동 중...\n")
        
        while True:
            schedule.run_pending()
            time.sleep(1)


# =========================================
# 실행
# =========================================

def main():
    """메인 실행"""
    scheduler = AutoTradingScheduler()
    scheduler.run()


if __name__ == '__main__':
    main()
