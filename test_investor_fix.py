#!/usr/bin/env python
"""투자자 매매 데이터 수집 버그 수정 테스트"""
import sys
sys.path.append('/home/user1/auto_trading')

from data_collection.crash_rebound_collector import CrashReboundDataCollector

# 수집기 생성
collector = CrashReboundDataCollector()

# 삼성전자 테스트
print("🧪 삼성전자 투자자 매매 데이터 수집 테스트...\n")
result = collector.collect_investor_trading('005930')

if result is not None:
    print("✅ 수집 성공!")
    print(f"\n최근 5일 데이터:")
    print(result.tail())
    
    print(f"\n통계:")
    print(f"  총 행: {len(result)}")
    print(f"  foreign_net 0이 아닌 행: {(result['foreign_net'] != 0).sum()} / {len(result)}")
    print(f"  institution_net 0이 아닌 행: {(result['institution_net'] != 0).sum()} / {len(result)}")
    print(f"  individual_net 0이 아닌 행: {(result['individual_net'] != 0).sum()} / {len(result)}")
    
    if (result['foreign_net'] != 0).sum() > 0:
        print("\n🎉 버그 수정 성공! 실제 데이터가 수집됩니다!")
    else:
        print("\n❌ 여전히 0만 있습니다. 추가 디버깅 필요")
else:
    print("❌ 수집 실패")
