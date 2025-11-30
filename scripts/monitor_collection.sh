#!/bin/bash
# 데이터 수집 진행 상황 모니터링

echo "📊 전체 종목 데이터 수집 진행 상황"
echo "="=================="

# 수집된 파일 수
total_files=$(ls -1 data/crash_rebound/*.parquet 2>/dev/null | wc -l)
echo "✅ 수집된 종목: $total_files개"

# 총 급락 횟수 (stats 파일에서)
if [ -f "data/crash_rebound/collection_stats.json" ]; then
    crashes=$(cat data/crash_rebound/collection_stats.json | grep total_crashes | grep -o '[0-9]\+')
    success=$(cat data/crash_rebound/collection_stats.json | grep successful_rebounds | grep -o '[0-9]\+')
    echo "📈 총 급락: ${crashes}회"
    echo "✅ 성공 반등: ${success}회"
fi

echo ""
echo "🔄 최근 수집 로그 (마지막 10줄):"
echo "--------------------------------"
tail -20 collection.log | grep -E "(종목|급락|저장)" | tail -10

echo ""
echo "💡 전체 로그 보기: tail -f collection.log"
echo "💡 수집 완료 확인: tail -100 collection.log | grep '완료'"
