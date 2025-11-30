# 💻 Windows 절전 모드 설정 확인 및 해제 방법

## 📊 현재 시스템 상태 (확인됨)

```
사용 가능한 절전 모드:
✅ 대기 모드 (S3) - Sleep
✅ 최대 절전 모드 - Hibernate  
✅ 빠른 시작
```

## ⚠️ 위험: 자동 절전 모드 진입하면 데이터 수집 중단!

---

## 🔍 설정 확인 방법 (Windows)

### 방법 1: 제어판에서 확인 (가장 쉬움)

1. **Windows 검색** → "전원 옵션" 입력
2. **전원 계획 선택** 클릭
3. 현재 계획 옆 **"계획 설정 변경"** 클릭
4. **고급 전원 관리 옵션 변경** 클릭
5. 다음 항목 확인:

```
절전
├─ 다음 시간 후 절전 모드
│  ├─ 전원 연결: 0분 (안 꺼짐) 또는 큰 값 (예: 999분)
│  └─ 배터리: 상관없음
│
└─ 다음 시간 후 최대 절전 모드  
   ├─ 전원 연결: 0분 (안 꺼짐) 또는 큰 값
   └─ 배터리: 상관없음
```

---

## ✅ 안전한 설정 (추천)

### 데이터 수집 중에는 이렇게 설정:

```
디스플레이
└─ 다음 시간 후 디스플레이 끄기
   └─ 전원 연결: 10분 ✅ (괜찮음, 화면만 꺼짐)

절전
└─ 다음 시간 후 절전 모드
   └─ 전원 연결: 안 함 ✅ (0분 또는 비활성화)

최대 절전 모드
└─ 다음 시간 후 최대 절전 모드
   └─ 전원 연결: 안 함 ✅ (0분 또는 비활성화)
```

---

## 🚀 빠른 설정 변경 (PowerShell 관리자 권한 필요)

```powershell
# 1. PowerShell을 관리자 권한으로 실행

# 2. 절전 모드 비활성화
powercfg -change -standby-timeout-ac 0

# 3. 최대 절전 모드 비활성화  
powercfg -change -hibernate-timeout-ac 0

# 4. 확인
powercfg /q SCHEME_CURRENT SUB_SLEEP
```

---

## 🛡️ 더 안전한 방법: 절전 모드 완전 비활성화 (임시)

```powershell
# 관리자 PowerShell에서:

# 1. 절전 모드 완전 비활성화
powercfg /x -standby-timeout-ac 0

# 2. 최대 절전 모드 비활성화
powercfg /x -hibernate-timeout-ac 0

# 3. 디스플레이만 끄기 (선택사항)
powercfg /x -monitor-timeout-ac 10
```

---

## 📱 실시간 확인 방법

### WSL에서 수집 중 확인:

```bash
# 1. tmux 세션 시작
tmux new -s data_collection

# 2. 수집 시작
cd /home/user1/auto_trading
python data_collection/enhanced_data_collector.py --mode investor

# 3. Ctrl+B, D로 분리

# 4. 언제든지 재접속
tmux attach -t data_collection

# 5. 진행 상황 확인
ls -lh data/enhanced/
```

---

## ⏰ 2~3일 안전하게 실행하는 체크리스트

### 시작 전 체크:
- [ ] 절전 모드: **안 함** (0분)
- [ ] 최대 절전 모드: **안 함** (0분)
- [ ] 디스플레이 끄기: **10분** (괜찮음)
- [ ] 전원 연결: **확인** (노트북이면 충전기 연결)
- [ ] tmux 세션 시작: **확인**

### 실행 중 확인:
- [ ] 매일 1번 tmux 재접속해서 진행 상황 확인
- [ ] 에러 없이 진행 중인지 확인
- [ ] 저장 파일 크기 증가 확인

---

## 🔴 만약 절전 모드로 들어갔다면?

1. **컴퓨터 깨우기**
2. **WSL 상태 확인**:
   ```bash
   wsl -l -v
   ```
3. **tmux 세션 복구 시도**:
   ```bash
   tmux ls  # 세션 목록 확인
   tmux attach -t data_collection  # 재접속 시도
   ```
4. **세션이 없으면**: 처음부터 다시 시작 😢

---

## 💡 최종 추천

### Option 1: 간단 설정 (Windows 제어판)
1. 전원 옵션 → 고급 설정
2. 절전: 0분 (안 함)
3. 최대 절전: 0분 (안 함)

### Option 2: tmux 사용 (안전)
```bash
tmux new -s data_collection
cd /home/user1/auto_trading
python data_collection/enhanced_data_collector.py --mode investor
# Ctrl+B, D로 분리
```

### Option 3: 클라우드 (가장 안전)
- AWS EC2, Google Cloud 무료 티어
- 로컬 컴퓨터 꺼도 됨
- 24시간 안정 실행

---

## 📞 문제 발생 시

1. **절전 모드 들어감**: 처음부터 다시
2. **WSL 종료됨**: 처음부터 다시
3. **중간 저장 없음**: 진행 파일 확인 (`data/enhanced/`)

**결론: 본체만 안 끄고, 절전 모드 0분 설정하면 안전합니다!**
