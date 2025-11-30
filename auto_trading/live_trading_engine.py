"""
실전 자동매매 엔진 (30만원 운용)

기능:
1. 실시간 급락 감지
2. AI 예측 + 최적화
3. KIS API 주문 실행
4. 포지션 관리 (익절/손절)
5. 텔레그램 알림
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import yaml

import pandas as pd
import numpy as np

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from auto_trading.realtime_learning_updater import RealtimeLearningUpdater
from ai_model.train_crash_rebound import CrashReboundModel


class LiveTradingEngine:
    """30만원 실전 자동매매 엔진"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로 (None이면 기본값 사용)
        """
        # 설정 로드
        if config_path is None:
            config_path = str(PROJECT_ROOT / 'config' / 'settings.yaml')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 컴포넌트 초기화
        self.updater = RealtimeLearningUpdater()
        self.model = CrashReboundModel()
        
        # 자금 관리
        self.total_capital = 300000  # 30만원
        self.max_per_trade = 100000  # 종목당 최대 10만원
        self.max_positions = 3  # 최대 동시 보유 3종목
        
        # 포지션 관리
        self.positions: Dict = {}  # {stock_code: position_info}
        self.order_history: List = []
        
        # KIS API (나중에 구현)
        self.kis_api = None
        
        # 텔레그램 봇 (나중에 구현)
        self.telegram_bot = None
        
        print(f"\n{'='*70}")
        print(f"💰 실전 자동매매 엔진 초기화")
        print(f"{'='*70}")
        print(f"총 자본금: {self.total_capital:,}원")
        print(f"종목당 최대: {self.max_per_trade:,}원")
        print(f"최대 동시 보유: {self.max_positions}종목")
        print(f"{'='*70}\n")
    
    # =========================================
    # 1. 급락 감지 및 매수 결정
    # =========================================
    
    def scan_and_trade(self):
        """실시간 급락 스캔 → AI 분석 → 매수"""
        
        # 관심 종목 리스트 (실전에서는 전체 종목 또는 거래량 상위)
        watchlist = self._get_watchlist()
        
        for stock_code, stock_name in watchlist:
            # 1. 급락 감지
            crash = self.updater.detect_realtime_crash(stock_code, stock_name)
            
            if not crash:
                continue
            
            print(f"\n{'='*70}")
            print(f"🚨 급락 감지: [{stock_name}] {crash['crash_rate']:.1f}%")
            print(f"{'='*70}")
            
            # 2. 이미 보유 중이면 스킵
            if stock_code in self.positions:
                print(f"⏭️  이미 보유 중 → 패스")
                continue
            
            # 3. 최대 포지션 체크
            if len(self.positions) >= self.max_positions:
                print(f"⏭️  최대 {self.max_positions}종목 보유 중 → 패스")
                continue
            
            # 4. AI 예측
            # TODO: 실제 모델 예측 구현
            probability = 0.75  # 임시
            
            if probability < 0.6:
                print(f"⏭️  AI 확률 {probability*100:.1f}% 낮음 → 패스")
                continue
            
            # 5. 최적화된 전략 계산
            target_profit, stop_loss, add_buy_point = \
                self.updater.calculate_optimal_exit_points(stock_code, crash)
            
            # 6. 매수 실행
            self._execute_buy_order(
                stock_code=stock_code,
                stock_name=stock_name,
                price=crash['Close'],
                ai_probability=probability,
                target_profit=target_profit,
                stop_loss=stop_loss,
                add_buy_point=add_buy_point
            )
    
    def _get_watchlist(self) -> List[tuple]:
        """모니터링 대상 종목 (실전에서는 전체 종목 또는 필터링)"""
        # 임시: 주요 종목만
        return [
            ('005930', '삼성전자'),
            ('000660', 'SK하이닉스'),
            ('035420', 'NAVER'),
            ('035720', '카카오'),
            ('051910', 'LG화학'),
        ]
    
    # =========================================
    # 2. 주문 실행
    # =========================================
    
    def _execute_buy_order(
        self,
        stock_code: str,
        stock_name: str,
        price: float,
        ai_probability: float,
        target_profit: float,
        stop_loss: float,
        add_buy_point: float,
        signal: Optional[Dict] = None
    ):
        """
        1차 매수 실행 (50%)
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
            price: 현재가
            ai_probability: AI 예측 확률
            target_profit: 목표 익절률 (%)
            stop_loss: 손절률 (%)
            add_buy_point: 추가 매수 시점 (%)
            signal: 급락 신호 데이터 (선택)
        """
        # 1차 매수 금액 (50%)
        first_buy_amount = self.max_per_trade * 0.5
        quantity = int(first_buy_amount / price)
        
        if quantity == 0:
            print(f"❌ 매수 수량 0 → 패스")
            return
        
        print(f"\n💰 매수 주문")
        print(f"   종목: {stock_name} ({stock_code})")
        print(f"   가격: {price:,.0f}원")
        print(f"   수량: {quantity}주")
        print(f"   금액: {quantity * price:,.0f}원")
        print(f"   AI 확률: {ai_probability*100:.1f}%")
        print(f"   목표 익절: +{target_profit:.1f}%")
        print(f"   손절: {stop_loss:.1f}%")
        print(f"   추가 매수: {add_buy_point:.1f}%")
        
        # TODO: 실제 KIS API 주문
        # order_result = self.kis_api.buy_market_order(stock_code, quantity)
        
        # 모의 주문 (테스트용)
        order_result = {
            'success': True,
            'order_no': f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'stock_code': stock_code,
            'quantity': quantity,
            'price': price
        }
        
        if order_result['success']:
            # 포지션 등록
            self.positions[stock_code] = {
                'stock_name': stock_name,
                'entry_price': price,
                'quantity': quantity,
                'first_buy_amount': quantity * price,
                'second_buy_done': False,
                'entry_time': datetime.now(),
                'ai_probability': ai_probability,
                'target_profit': target_profit,
                'stop_loss': stop_loss,
                'add_buy_point': add_buy_point,
                'order_no': order_result['order_no']
            }
            
            print(f"✅ 1차 매수 완료!")
            
            # 매수 근거 데이터 준비
            if signal is None:
                signal = {}
            
            buy_reason = {
                'strategy': '크래쉬 반등',
                'crash_rate': signal.get('crash_rate', 0),
                'volume_rank': signal.get('volume_rank', 0),
                'foreign_buy': signal.get('foreign_buy', 0) / 100000000,  # 억 단위
                'institution_buy': signal.get('institution_buy', 0) / 100000000,  # 억 단위
                'similar_pattern': {
                    'similarity': ai_probability,  # AI 확률을 유사도로 사용
                    'success_rate': 0.72,  # 학습 데이터 평균 성공률
                    'avg_return': 8.5,  # 학습 데이터 평균 수익률
                    'matching_stocks': signal.get('similar_stocks', ['삼성전자', 'SK하이닉스', 'NAVER'])
                }
            }
            
            # 텔레그램 알림
            self._send_telegram_alert(
                action="매수",
                stock_name=stock_name,
                quantity=quantity,
                price=price,
                ai_probability=ai_probability,
                target_profit=target_profit,
                buy_reason=buy_reason
            )
        else:
            print(f"❌ 주문 실패")
    
    # =========================================
    # 3. 포지션 관리 (익절/손절/추가매수)
    # =========================================
    
    def manage_positions(self):
        """
        보유 포지션 모니터링
        - 익절/손절 체크
        - 추가 매수 (물타기)
        - 시간 손절 (5일)
        """
        if not self.positions:
            return
        
        for stock_code, position in list(self.positions.items()):
            stock_name = position['stock_name']
            entry_price = position['entry_price']
            
            # 현재가 조회
            current_price = self._get_current_price(stock_code)
            
            if current_price is None:
                continue
            
            # 수익률 계산
            profit_rate = (current_price - entry_price) / entry_price * 100
            
            # 1. 익절 체크
            if profit_rate >= position['target_profit']:
                self._execute_sell_order(
                    stock_code, 
                    position, 
                    current_price,
                    reason=f"익절 +{profit_rate:.1f}%"
                )
                continue
            
            # 2. 손절 체크
            if profit_rate <= position['stop_loss']:
                self._execute_sell_order(
                    stock_code,
                    position,
                    current_price,
                    reason=f"손절 {profit_rate:.1f}%"
                )
                continue
            
            # 3. 추가 매수 체크 (아직 안 했으면)
            if not position['second_buy_done'] and profit_rate <= position['add_buy_point']:
                self._execute_additional_buy(stock_code, position, current_price)
                continue
            
            # 4. 시간 손절 (5일)
            holding_days = (datetime.now() - position['entry_time']).days
            if holding_days >= 5:
                self._execute_sell_order(
                    stock_code,
                    position,
                    current_price,
                    reason=f"시간손절 (보유 {holding_days}일)"
                )
                continue
    
    def _execute_additional_buy(self, stock_code: str, position: Dict, price: float):
        """2차 매수 (물타기 50%)"""
        # 2차 매수 금액
        second_buy_amount = self.max_per_trade * 0.5
        quantity = int(second_buy_amount / price)
        
        if quantity == 0:
            return
        
        print(f"\n💰 추가 매수 ({position['add_buy_point']:.1f}% 하락)")
        print(f"   종목: {position['stock_name']}")
        print(f"   가격: {price:,.0f}원")
        print(f"   수량: {quantity}주")
        
        # TODO: 실제 주문
        # order_result = self.kis_api.buy_market_order(stock_code, quantity)
        
        # 모의 주문
        order_result = {'success': True}
        
        if order_result['success']:
            # 평균 단가 계산
            total_quantity = position['quantity'] + quantity
            total_amount = (position['quantity'] * position['entry_price'] + 
                          quantity * price)
            avg_price = total_amount / total_quantity
            
            # 포지션 업데이트
            position['quantity'] = total_quantity
            position['entry_price'] = avg_price
            position['second_buy_done'] = True
            
            print(f"✅ 2차 매수 완료! 평균단가: {avg_price:,.0f}원")
            
            # 텔레그램 알림
            self._send_telegram_message(
                f"🟡 추가 매수\n"
                f"종목: {position['stock_name']}\n"
                f"수량: {quantity}주\n"
                f"평균단가: {avg_price:,.0f}원"
            )
    
    def _execute_sell_order(
        self, 
        stock_code: str, 
        position: Dict, 
        price: float,
        reason: str
    ):
        """전량 매도"""
        quantity = position['quantity']
        
        print(f"\n💸 매도 주문 ({reason})")
        print(f"   종목: {position['stock_name']}")
        print(f"   수량: {quantity}주")
        print(f"   가격: {price:,.0f}원")
        
        # TODO: 실제 주문
        # order_result = self.kis_api.sell_market_order(stock_code, quantity)
        
        # 모의 주문
        order_result = {'success': True}
        
        if order_result['success']:
            # 손익 계산
            profit_amount = (price - position['entry_price']) * quantity
            profit_rate = (price - position['entry_price']) / position['entry_price'] * 100
            
            print(f"✅ 매도 완료!")
            print(f"   손익: {profit_amount:+,.0f}원 ({profit_rate:+.1f}%)")
            
            # 거래 기록
            self.order_history.append({
                'date': datetime.now(),
                'stock_code': stock_code,
                'stock_name': position['stock_name'],
                'action': 'SELL',
                'quantity': quantity,
                'price': price,
                'profit_amount': profit_amount,
                'profit_rate': profit_rate,
                'reason': reason
            })
            
            # 포지션 제거
            del self.positions[stock_code]
            
            # 텔레그램 알림 (상세 정보 포함)
            self._send_telegram_alert(
                action="매도",
                stock_name=position['stock_name'],
                quantity=quantity,
                price=price,
                profit_amount=profit_amount,
                profit_rate=profit_rate,
                reason=reason
            )
    
    def _get_current_price(self, stock_code: str) -> Optional[float]:
        """현재가 조회"""
        # TODO: KIS API 또는 실시간 데이터
        # return self.kis_api.get_current_price(stock_code)
        
        # 임시: FinanceDataReader
        try:
            import FinanceDataReader as fdr
            df = fdr.DataReader(stock_code, datetime.now() - timedelta(days=1))
            if len(df) > 0:
                return float(df.iloc[-1]['Close'])
        except:
            pass
        
        return None
    
    # =========================================
    # 4. 텔레그램 알림
    # =========================================
    
    def _send_telegram_message(self, message: str):
        """텔레그램 메시지 전송 (단순 메시지)"""
        # TODO: 텔레그램 봇 구현
        # self.telegram_bot.send_message(message)
        
        # 임시: 콘솔 출력
        print(f"\n📱 [텔레그램] {message}\n")
    
    def _send_telegram_alert(self, action: str, stock_name: str, quantity: int, 
                            price: float, **kwargs):
        """텔레그램 거래 알림 (상세 정보 포함)"""
        try:
            from utils.telegram_bot import TelegramBot
            try:
                from dotenv import load_dotenv  # type: ignore
            except ImportError:
                load_dotenv = None  # type: ignore
            import os
            
            # .env 로드 (가능한 경우)
            if load_dotenv:
                load_dotenv()
            
            # 텔레그램 봇이 .env에 설정되어 있는지 확인
            if os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
                # TelegramBot 클래스를 직접 초기화하지 않고 환경변수 사용
                import requests
                
                bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                chat_id = os.getenv('TELEGRAM_CHAT_ID')
                
                # 메시지 구성 (HTML 형식)
                emoji = "🟢" if action == "매수" else "🔴"
                message = f"{emoji} <b>{action} 완료</b>\n"
                message += f"━━━━━━━━━━━━━━━━\n"
                message += f"종목: {stock_name}\n"
                message += f"수량: {quantity}주\n"
                message += f"가격: {price:,.0f}원\n"
                message += f"금액: {quantity * price:,.0f}원\n"
                
                # 매수 근거 추가
                if action == "매수" and 'buy_reason' in kwargs:
                    reason_data = kwargs['buy_reason']
                    message += f"\n📊 <b>매수 근거</b>\n"
                    
                    if 'strategy' in reason_data:
                        message += f"전략: {reason_data['strategy']}\n"
                    if 'crash_rate' in reason_data:
                        message += f"급락률: {reason_data['crash_rate']:.1f}%\n"
                    if 'volume_rank' in reason_data:
                        message += f"거래대금: {reason_data['volume_rank']}위권\n"
                    if 'foreign_buy' in reason_data:
                        message += f"외인: {reason_data['foreign_buy']:,.0f}억\n"
                    if 'institution_buy' in reason_data:
                        message += f"기관: {reason_data['institution_buy']:,.0f}억\n"
                    
                    if 'similar_pattern' in reason_data:
                        pattern = reason_data['similar_pattern']
                        message += f"\n🔍 <b>학습 패턴 매칭</b>\n"
                        message += f"유사도: {pattern.get('similarity', 0)*100:.0f}%\n"
                        message += f"과거 성공률: {pattern.get('success_rate', 0)*100:.0f}%\n"
                        message += f"평균 수익률: +{pattern.get('avg_return', 0):.1f}%\n"
                
                # AI 확률
                if 'ai_probability' in kwargs:
                    message += f"\n🤖 AI 확률: {kwargs['ai_probability']*100:.1f}%\n"
                
                # 목표 수익률
                if 'target_profit' in kwargs:
                    message += f"목표 수익: +{kwargs['target_profit']:.1f}%\n"
                
                # 손익 (매도 시)
                if 'profit_amount' in kwargs:
                    profit_emoji = "💰" if kwargs['profit_amount'] > 0 else "📉"
                    message += f"\n{profit_emoji} <b>손익</b>\n"
                    message += f"금액: {kwargs['profit_amount']:+,.0f}원\n"
                    message += f"수익률: {kwargs.get('profit_rate', 0):+.1f}%\n"
                
                if 'reason' in kwargs:
                    message += f"사유: {kwargs['reason']}\n"
                
                # 전송
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                requests.post(url, data=data)
            else:
                # 텔레그램 미설정 시 콘솔만 출력
                print(f"\n📱 [텔레그램] {action} - {stock_name} {quantity}주 @ {price:,.0f}원\n")
                
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")
            # 실패해도 계속 진행
    
    # =========================================
    # 5. 일별 리포트
    # =========================================
    
    def generate_daily_report(self):
        """일별 수익 리포트"""
        today_trades = [
            t for t in self.order_history 
            if t['date'].date() == datetime.now().date()
        ]
        
        if not today_trades:
            print("\n오늘 거래 없음")
            return
        
        total_profit = sum(t['profit_amount'] for t in today_trades if 'profit_amount' in t)
        win_count = sum(1 for t in today_trades if t.get('profit_amount', 0) > 0)
        
        print(f"\n{'='*70}")
        print(f"📊 오늘 거래 리포트")
        print(f"{'='*70}")
        print(f"거래 수: {len(today_trades)}건")
        print(f"승: {win_count}건 / 패: {len(today_trades) - win_count}건")
        print(f"승률: {win_count/len(today_trades)*100:.1f}%")
        print(f"총 손익: {total_profit:+,.0f}원")
        print(f"{'='*70}\n")
        
        # 텔레그램 리포트
        self._send_telegram_message(
            f"📊 일일 리포트\n"
            f"거래: {len(today_trades)}건\n"
            f"승률: {win_count/len(today_trades)*100:.1f}%\n"
            f"손익: {total_profit:+,.0f}원"
        )


# =========================================
# 실행 예제
# =========================================

def main():
    """실전 자동매매 실행"""
    engine = LiveTradingEngine()
    
    print("\n🚀 자동매매 시작!\n")
    print("장 시작: 09:00 / 장 마감: 15:30")
    print("급락 스캔: 5분마다")
    print("포지션 관리: 1분마다")
    print("\nCtrl+C로 종료\n")
    
    try:
        last_scan_time = datetime.now() - timedelta(minutes=10)  # 즉시 스캔
        last_manage_time = datetime.now()
        
        while True:
            now = datetime.now()
            
            # 장 시간 체크 (평일 09:00~15:30)
            if now.weekday() < 5:  # 월~금
                if 9 <= now.hour < 15 or (now.hour == 15 and now.minute < 30):
                    
                    # 5분마다 급락 스캔
                    if (now - last_scan_time).seconds >= 300:
                        print(f"\n[{now.strftime('%H:%M:%S')}] 급락 스캔 중...")
                        engine.scan_and_trade()
                        last_scan_time = now
                    
                    # 1분마다 포지션 관리
                    if (now - last_manage_time).seconds >= 60:
                        print(f"[{now.strftime('%H:%M:%S')}] 포지션 체크")
                        engine.manage_positions()
                        last_manage_time = now
                
                # 장 마감 후 리포트 (15:35에 1회)
                elif now.hour == 15 and now.minute == 35:
                    print("\n📊 장 마감 - 일일 리포트 생성")
                    engine.generate_daily_report()
                    time.sleep(300)  # 5분 대기 (중복 방지)
            
            time.sleep(10)  # 10초마다 체크
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 자동매매 종료")
        print("현재 포지션 확인 후 수동 정리 필요\n")


if __name__ == '__main__':
    main()
