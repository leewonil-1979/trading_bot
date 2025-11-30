"""
텔레그램 봇 - 거래 알림
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional
import yaml
import requests


class TelegramBot:
    """텔레그램 봇 알림"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로
        """
        # 설정 로드
        if config_path is None:
            PROJECT_ROOT = Path(__file__).parent.parent
            config_path = str(PROJECT_ROOT / 'config' / 'settings.yaml')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 텔레그램 설정
        telegram_config = config.get('telegram', {})
        self.token = telegram_config.get('bot_token', '')
        self.chat_id = telegram_config.get('chat_id', '')
        
        # 텔레그램 봇 활성화 여부
        self.enabled = bool(self.token and self.chat_id and 
                          self.token != 'YOUR_BOT_TOKEN')
        
        if self.enabled:
            print(f"✅ 텔레그램 봇 활성화")
        else:
            print(f"⚠️  텔레그램 봇 비활성화 (설정 필요)")
    
    def send_message(self, message: str) -> bool:
        """
        메시지 전송
        
        Args:
            message: 전송할 메시지
            
        Returns:
            성공 여부
        """
        if not self.enabled:
            # 콘솔에만 출력
            print(f"\n📱 [텔레그램] {message}\n")
            return False
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
        data = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'  # HTML 형식 지원
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"❌ 텔레그램 전송 실패: {e}")
            return False
    
    def send_trade_alert(
        self,
        action: str,
        stock_name: str,
        quantity: int,
        price: float,
        **kwargs
    ):
        """
        거래 알림
        
        Args:
            action: 매수/매도
            stock_name: 종목명
            quantity: 수량
            price: 가격
            **kwargs: 추가 정보 (ai_probability, target_profit, profit_amount 등)
        """
        emoji = "🟢" if action == "매수" else "🔴"
        
        message = f"{emoji} <b>{action} 완료</b>\n"
        message += f"━━━━━━━━━━━━━━━━\n"
        message += f"종목: {stock_name}\n"
        message += f"수량: {quantity}주\n"
        message += f"가격: {price:,.0f}원\n"
        message += f"금액: {quantity * price:,.0f}원\n"
        
        # 매수 이유 (상세)
        if action == "매수" and 'buy_reason' in kwargs:
            message += f"\n📊 <b>매수 근거</b>\n"
            reason_data = kwargs['buy_reason']
            
            # 전략 유형
            if 'strategy' in reason_data:
                message += f"전략: {reason_data['strategy']}\n"
            
            # 급락률
            if 'crash_rate' in reason_data:
                message += f"급락률: {reason_data['crash_rate']:.1f}%\n"
            
            # 거래대금 순위
            if 'volume_rank' in reason_data:
                message += f"거래대금: {reason_data['volume_rank']}위권\n"
            
            # 외인/기관 매수
            if 'foreign_buy' in reason_data:
                message += f"외인: {reason_data['foreign_buy']:,.0f}억\n"
            if 'institution_buy' in reason_data:
                message += f"기관: {reason_data['institution_buy']:,.0f}억\n"
            
            # 유사 패턴
            if 'similar_pattern' in reason_data:
                pattern = reason_data['similar_pattern']
                message += f"\n🔍 <b>학습 패턴 매칭</b>\n"
                message += f"유사도: {pattern.get('similarity', 0)*100:.0f}%\n"
                message += f"과거 성공률: {pattern.get('success_rate', 0)*100:.0f}%\n"
                message += f"평균 수익률: +{pattern.get('avg_return', 0):.1f}%\n"
                
                if 'matching_stocks' in pattern:
                    message += f"유사 종목: {', '.join(pattern['matching_stocks'][:3])}\n"
        
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
        
        # 매도 사유
        if 'reason' in kwargs:
            message += f"사유: {kwargs['reason']}\n"
        
        self.send_message(message)
    
    def send_daily_report(
        self,
        trade_count: int,
        win_count: int,
        total_profit: float,
        positions_count: int
    ):
        """
        일일 리포트
        
        Args:
            trade_count: 거래 횟수
            win_count: 승리 횟수
            total_profit: 총 손익
            positions_count: 현재 보유 종목 수
        """
        if trade_count == 0:
            return
        
        win_rate = win_count / trade_count * 100
        emoji = "📈" if total_profit > 0 else "📉"
        
        message = f"{emoji} <b>일일 거래 리포트</b>\n"
        message += f"━━━━━━━━━━━━━━━━\n"
        message += f"거래: {trade_count}건\n"
        message += f"승: {win_count}건 / 패: {trade_count - win_count}건\n"
        message += f"승률: {win_rate:.1f}%\n"
        message += f"손익: {total_profit:+,.0f}원\n"
        message += f"보유 종목: {positions_count}개\n"
        
        self.send_message(message)


# =========================================
# 설정 파일에 텔레그램 설정 추가
# =========================================

def setup_telegram_config():
    """설정 파일에 텔레그램 섹션 추가"""
    
    config_path = str(Path(__file__).parent.parent / 'config' / 'settings.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 텔레그램 설정이 없으면 추가
    if 'telegram' not in config:
        config['telegram'] = {
            'bot_token': 'YOUR_BOT_TOKEN',
            'chat_id': 'YOUR_CHAT_ID'
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 텔레그램 설정 추가됨: {config_path}")
        print(f"\n📝 설정 방법:")
        print(f"   1. @BotFather에서 봇 생성 → 토큰 받기")
        print(f"   2. 봇과 대화 시작")
        print(f"   3. https://api.telegram.org/bot<토큰>/getUpdates 에서 chat_id 확인")
        print(f"   4. settings.yaml에 bot_token과 chat_id 입력\n")


# =========================================
# 테스트
# =========================================

def main():
    """테스트 실행"""
    
    # 설정 추가
    setup_telegram_config()
    
    # 봇 초기화
    bot = TelegramBot()
    
    print("\n🧪 텔레그램 봇 테스트\n")
    
    # 1. 매수 알림
    print("1️⃣ 매수 알림")
    bot.send_trade_alert(
        action="매수",
        stock_name="삼성전자",
        quantity=10,
        price=70000,
        ai_probability=0.85,
        target_profit=15.0
    )
    
    # 2. 매도 알림
    print("2️⃣ 매도 알림")
    bot.send_trade_alert(
        action="매도",
        stock_name="삼성전자",
        quantity=10,
        price=75000,
        profit_amount=50000,
        profit_rate=7.14,
        reason="익절"
    )
    
    # 3. 일일 리포트
    print("3️⃣ 일일 리포트")
    bot.send_daily_report(
        trade_count=5,
        win_count=4,
        total_profit=150000,
        positions_count=2
    )


if __name__ == '__main__':
    main()
