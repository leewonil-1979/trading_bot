"""
급락 후 반등 매매 전략 (이시다 스타일)

핵심 로직:
1. 비정상적 급락 감지 (-20~30%)
2. 급락 원인 분석 (뉴스, 공시, 기술적)
3. 반등 가능성 예측 (AI)
4. 최적 진입 타이밍 (급락 다음날 or 반등 첫날 시초가)
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from pykrx import stock
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ta  # pip install ta

# dart_fss는 Python 3.9+에서만 지원 - 선택적 import
dart = None


class CrashReboundDetector:
    """급락 종목 감지 및 반등 예측"""
    
    def __init__(self, dart_api_key=None):
        self.dart_api_key = dart_api_key
        if dart_api_key and dart is not None:
            dart.set_api_key(dart_api_key)
    
    # =========================================
    # 1. 급락 감지
    # =========================================
    
    def detect_crash(self, days_back=5):
        """
        비정상적 급락 종목 감지
        
        Args:
            days_back: 최근 며칠 스캔
            
        Returns:
            급락 종목 리스트
        """
        print(f"\n{'='*60}")
        print(f"🔍 급락 종목 스캔 (최근 {days_back}일)")
        print(f"{'='*60}\n")
        
        # 전체 종목 리스트
        stocks = fdr.StockListing('KRX')
        crash_stocks = []
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back + 30)  # 여유있게
        
        for idx, row in stocks.iterrows():
            stock_code = row['Code']
            stock_name = row['Name']
            
            try:
                # 일봉 데이터
                df = fdr.DataReader(stock_code, start_date)
                
                if len(df) < days_back:
                    continue
                
                # 최근 급락 확인
                recent = df.tail(days_back)
                
                for i in range(len(recent)):
                    day_data = recent.iloc[i]
                    prev_close = recent.iloc[i-1]['Close'] if i > 0 else day_data['Open']
                    
                    # 급락률 계산
                    crash_rate = (day_data['Close'] - prev_close) / prev_close * 100
                    
                    # 급락 기준: -15% 이상
                    if crash_rate <= -15:
                        
                        # 급락 상세 정보
                        crash_info = {
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'crash_date': day_data.name.strftime('%Y-%m-%d'),  # type: ignore
                            'crash_rate': crash_rate,
                            'volume_spike': day_data['Volume'] / df['Volume'].rolling(20).mean().iloc[-1],
                            'prev_close': prev_close,
                            'crash_price': day_data['Close'],
                            'low': day_data['Low'],
                            'high': day_data['High'],
                            'volume': day_data['Volume']
                        }
                        
                        crash_stocks.append(crash_info)
                        
                        print(f"🚨 [{stock_name}] {crash_rate:.1f}% 급락!")
                        print(f"   날짜: {crash_info['crash_date']}")
                        print(f"   거래량 급증: {crash_info['volume_spike']:.1f}배\n")
                
            except Exception as e:
                continue
        
        print(f"\n총 {len(crash_stocks)}개 급락 종목 발견!\n")
        return pd.DataFrame(crash_stocks)
    
    # =========================================
    # 2. 급락 원인 분석
    # =========================================
    
    def analyze_crash_reason(self, stock_code, crash_date):
        """
        급락 원인 분석
        
        Returns:
            {
                'news': [...],
                'disclosure': [...],
                'technical': {...},
                'investor': {...}
            }
        """
        print(f"\n📊 급락 원인 분석: {stock_code} ({crash_date})")
        
        result = {}
        
        # 1. 뉴스 분석
        result['news'] = self._analyze_news(stock_code, crash_date)
        
        # 2. 공시 분석
        result['disclosure'] = self._analyze_disclosure(stock_code, crash_date)
        
        # 3. 기술적 분석
        result['technical'] = self._analyze_technical(stock_code, crash_date)
        
        # 4. 투자자 매매 분석
        result['investor'] = self._analyze_investor_trading(stock_code, crash_date)
        
        return result
    
    def _analyze_news(self, stock_code, crash_date):
        """뉴스 수집 및 감성 분석"""
        try:
            url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_list = []
            for item in soup.select('table.type5 tr')[:10]:
                link = item.select_one('a.tit')
                if link:
                    news = {
                        'title': link.text.strip(),
                        'url': 'https://finance.naver.com' + str(link.get('href', '')),  # type: ignore
                        'sentiment': self._sentiment_analysis(link.text)
                    }
                    news_list.append(news)
            
            print(f"   📰 뉴스 {len(news_list)}건 수집")
            
            # 악재 뉴스 카운트
            negative = sum(1 for n in news_list if n['sentiment'] == 'negative')
            print(f"   악재 뉴스: {negative}건")
            
            return news_list
            
        except Exception as e:
            print(f"   뉴스 수집 오류: {e}")
            return []
    
    def _sentiment_analysis(self, text):
        """간단한 감성 분석"""
        negative_keywords = [
            '급락', '하락', '악재', '손실', '적자', '부진', '감소',
            '횡령', '분식', '소송', '과징금', '영업정지', '적발',
            '부도', '워크아웃', '회생', '파산', '폐업'
        ]
        
        positive_keywords = [
            '급등', '상승', '호재', '이익', '성장', '증가',
            '수주', '계약', '특허', '신제품', '개발', '투자유치'
        ]
        
        neg_count = sum(1 for kw in negative_keywords if kw in text)
        pos_count = sum(1 for kw in positive_keywords if kw in text)
        
        if neg_count > pos_count:
            return 'negative'
        elif pos_count > neg_count:
            return 'positive'
        else:
            return 'neutral'
    
    def _analyze_disclosure(self, stock_code, crash_date):
        """공시 분석 (DART)"""
        if not self.dart_api_key:
            return []
        
        try:
            # DART API로 공시 조회
            # (실제 구현 시 dart_fss 라이브러리 사용)
            print(f"   📢 공시 조회 중...")
            
            # TODO: DART API 구현
            return []
            
        except Exception as e:
            print(f"   공시 조회 오류: {e}")
            return []
    
    def _analyze_technical(self, stock_code, crash_date):
        """기술적 지표 분석"""
        try:
            # 과거 1년 데이터
            df = fdr.DataReader(stock_code, '2024-01-01')
            
            if len(df) < 50:
                return {}
            
            # 기술적 지표 계산
            df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()  # type: ignore
            df['MACD'] = ta.trend.MACD(df['Close']).macd()  # type: ignore
            df['BB_upper'] = ta.volatility.BollingerBands(df['Close']).bollinger_hband()  # type: ignore
            df['BB_lower'] = ta.volatility.BollingerBands(df['Close']).bollinger_lband()  # type: ignore
            
            # 급락일 데이터
            crash_idx = df.index.get_loc(pd.to_datetime(crash_date))
            crash_data = df.iloc[crash_idx]
            
            technical = {
                'rsi': crash_data['RSI'],
                'macd': crash_data['MACD'],
                'oversold': crash_data['RSI'] < 30,  # 과매도
                'below_bb_lower': crash_data['Close'] < crash_data['BB_lower'],  # 볼린저 하단 이탈
                'volume_20d_avg': df['Volume'].rolling(20).mean().iloc[crash_idx],
                'volume_spike': crash_data['Volume'] / df['Volume'].rolling(20).mean().iloc[crash_idx]
            }
            
            print(f"   📈 RSI: {technical['rsi']:.1f} ({'과매도' if technical['oversold'] else '정상'})")
            print(f"   📊 거래량 급증: {technical['volume_spike']:.1f}배")
            
            return technical
            
        except Exception as e:
            print(f"   기술적 분석 오류: {e}")
            return {}
    
    def _analyze_investor_trading(self, stock_code, crash_date):
        """투자자별 매매 분석 (프로그램, 외국인 등)"""
        try:
            # pykrx로 투자자별 매매 조회
            start = (pd.to_datetime(crash_date) - timedelta(days=30)).strftime('%Y%m%d')
            end = pd.to_datetime(crash_date).strftime('%Y%m%d')
            
            df = stock.get_market_trading_value_by_date(start, end, stock_code)
            
            if df.empty:
                return {}
            
            # 급락일 데이터
            crash_trading = df.loc[crash_date] if crash_date in df.index else df.iloc[-1]
            
            investor = {
                'institution_net': crash_trading['기관'],
                'foreign_net': crash_trading['외국인'],
                'individual_net': crash_trading['개인'],
                'institution_selling': crash_trading['기관'] < -100000000,  # 1억 이상 순매도
                'foreign_selling': crash_trading['외국인'] < -100000000
            }
            
            print(f"   💼 기관 순매수: {investor['institution_net']:,.0f}원")
            print(f"   🌏 외국인 순매수: {investor['foreign_net']:,.0f}원")
            
            return investor
            
        except Exception as e:
            print(f"   투자자 매매 분석 오류: {e}")
            return {}
    
    # =========================================
    # 3. 반등 예측
    # =========================================
    
    def predict_rebound(self, crash_analysis):
        """
        반등 가능성 점수 계산
        
        Returns:
            점수 (0~100), 높을수록 반등 가능성 높음
        """
        score = 50  # 기본 50점
        
        # 1. 뉴스 분석 (±20점)
        news = crash_analysis.get('news', [])
        if news:
            negative_ratio = sum(1 for n in news if n['sentiment'] == 'negative') / len(news)
            if negative_ratio < 0.3:  # 악재 뉴스 적음
                score += 20
            elif negative_ratio > 0.7:  # 악재 뉴스 많음
                score -= 20
        
        # 2. 공시 분석 (±15점)
        disclosure = crash_analysis.get('disclosure', [])
        # TODO: 공시 영향도 분석
        
        # 3. 기술적 분석 (±25점)
        technical = crash_analysis.get('technical', {})
        if technical:
            # 과매도
            if technical.get('oversold'):
                score += 15
            
            # 볼린저 하단 이탈
            if technical.get('below_bb_lower'):
                score += 10
        
        # 4. 투자자 매매 (±20점)
        investor = crash_analysis.get('investor', {})
        if investor:
            # 외국인/기관 동반 매도 = 악재
            if investor.get('institution_selling') and investor.get('foreign_selling'):
                score -= 20
            # 외국인/기관 매수 = 호재
            elif investor.get('institution_net', 0) > 0 and investor.get('foreign_net', 0) > 0:
                score += 20
        
        # 점수 범위 0~100
        score = max(0, min(100, score))
        
        print(f"\n✨ 반등 가능성 점수: {score}/100")
        
        if score >= 70:
            print("   → 💚 반등 가능성 높음!")
        elif score >= 50:
            print("   → 💛 중립")
        else:
            print("   → 💔 반등 가능성 낮음")
        
        return score
    
    # =========================================
    # 4. 매수 타이밍
    # =========================================
    
    def find_entry_timing(self, stock_code, crash_date, rebound_score):
        """
        최적 매수 타이밍 찾기
        
        Returns:
            {
                'strategy': 'next_day_open' or 'wait_rebound',
                'target_price': 목표가,
                'stop_loss': 손절가
            }
        """
        print(f"\n🎯 매수 타이밍 전략")
        
        # 일봉 데이터
        df = fdr.DataReader(stock_code, crash_date)
        
        if len(df) < 2:
            return None
        
        crash_price = float(df.loc[crash_date, 'Close'])  # type: ignore
        crash_low = float(df.loc[crash_date, 'Low'])  # type: ignore
        
        # 반등 점수 높으면 → 다음날 시초가 매수
        if rebound_score >= 70:
            strategy = {
                'strategy': 'next_day_open',
                'description': '급락 다음날 시초가 매수 (공격적)',
                'entry': '다음날 시초가',
                'target_price': crash_price * 1.15,  # +15% 목표
                'stop_loss': crash_low * 0.95  # 최저가 -5%
            }
            
            print(f"   전략: {strategy['description']}")
            print(f"   진입: {strategy['entry']}")
            print(f"   목표가: {strategy['target_price']:,.0f}원 (+15%)")
            print(f"   손절가: {strategy['stop_loss']:,.0f}원")
        
        # 반등 점수 중간 → 반등 확인 후 매수
        else:
            strategy = {
                'strategy': 'wait_rebound',
                'description': '반등 첫날 시초가 매수 (안전)',
                'entry': '전일 대비 +3% 이상 시 시초가',
                'target_price': crash_price * 1.10,  # +10% 목표
                'stop_loss': crash_low * 0.97  # 최저가 -3%
            }
            
            print(f"   전략: {strategy['description']}")
            print(f"   진입 조건: {strategy['entry']}")
            print(f"   목표가: {strategy['target_price']:,.0f}원 (+10%)")
            print(f"   손절가: {strategy['stop_loss']:,.0f}원")
        
        return strategy


# =========================================
# 실행 예제
# =========================================

def main():
    """급락 후 반등 매매 전략 실행"""
    
    print("\n" + "="*60)
    print("🚀 급락 후 반등 매매 전략 (이시다 스타일)")
    print("="*60)
    
    # 1. 급락 종목 감지
    detector = CrashReboundDetector(dart_api_key='YOUR_DART_API_KEY')
    
    crash_stocks = detector.detect_crash(days_back=5)
    
    if crash_stocks.empty:
        print("\n최근 급락 종목이 없습니다.")
        return
    
    # 2. 급락 종목별 분석
    for idx, crash in crash_stocks.iterrows():
        print("\n" + "="*60)
        print(f"분석 대상: {crash['stock_name']} ({crash['stock_code']})")
        print(f"급락일: {crash['crash_date']}, 급락률: {crash['crash_rate']:.1f}%")
        print("="*60)
        
        # 원인 분석
        analysis = detector.analyze_crash_reason(
            crash['stock_code'],
            crash['crash_date']
        )
        
        # 반등 예측
        rebound_score = detector.predict_rebound(analysis)
        
        # 매수 타이밍
        if rebound_score >= 50:  # 50점 이상만 거래
            timing = detector.find_entry_timing(
                crash['stock_code'],
                crash['crash_date'],
                rebound_score
            )
            
            print(f"\n💡 추천: {timing['description']}")  # type: ignore
        else:
            print(f"\n⚠️ 반등 가능성 낮음 → 패스")
    
    print("\n" + "="*60)
    print("✅ 분석 완료!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
