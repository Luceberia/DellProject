# Dell iDRAC Monitor

Dell 서버의 iDRAC을 모니터링하고 관리하는 PyQt6 기반 데스크톱 애플리케이션입니다.

## 주요 기능

### 1. 서버 모니터링
- 실시간 서버 상태 모니터링 (지원 예정)
- CPU, 메모리, 전원 상태 등 하드웨어 정보 실시간 조회
- 시스템 이벤트 로그(SEL) 실시간 모니터링 (지원 예정)
- 서버 성능 메트릭 그래프 표시

### 2. 하드웨어 관리
- CPU, 메모리, 스토리지 등 하드웨어 상세 정보 조회
- 팬 속도 및 전원 소비량 모니터링
- 하드웨어 인벤토리 관리
- 센서 상태 모니터링

### 3. 시스템 이벤트 관리
- 시스템 이벤트 로그(SEL) 조회 및 관리
- 이벤트 심각도별 필터링
- 이벤트 알림 설정
- 이벤트 로그 내보내기

### 4. 서버 설정 관리
- 서버 추가/수정/삭제
- iDRAC 접속 정보 관리
- 서버 그룹 관리(지원 예정)
- 모니터링 주기 설정

## 프로젝트 구조

```
app/
├── common/          # 공통 유틸리티 모듈
│   ├── cache/      # 캐시 관리
│   │   └── cache_manager.py    # 캐시 처리 로직
│   ├── data/       # 데이터 처리
│   │   └── data_processor.py   # 데이터 처리 유틸리티
│   └── hardware/   # 하드웨어 정보 처리
│       └── hardware_info.py    # 하드웨어 정보 수집
├── config/         # 설정 관련 모듈
│   ├── data/       # 데이터 설정
│   │   └── models.py          # 데이터 모델 정의
│   ├── server/     # 서버 설정
│   │   ├── dell_config.py     # Dell 서버 설정
│   │   └── server_config.py   # 서버 연결 설정
│   └── system/     # 시스템 설정
│       ├── app_config.py      # 앱 설정
│       └── log_config.py      # 로깅 설정
├── dell_logging/   # 로깅 모듈
│   └── logger.py   # 로그 처리
├── endpoints/      # Redfish API 엔드포인트
│   └── redfish_endpoints.py   # API 엔드포인트 정의
├── error/          # 에러 처리
│   └── error_handler.py       # 에러 처리 로직
├── icon/           # UI 아이콘
├── managers/       # 서버 관리 모듈
│   └── dell_server_manager.py # 서버 관리 로직
├── network/        # 네트워크 연결 관리
│   └── connection_manager.py  # 연결 관리
├── ui/             # UI 컴포넌트
│   ├── main_window.py        # 메인 윈도우
│   └── components/ # UI 구성 요소
│       ├── hardware_section.py # 하드웨어 섹션
│       ├── monitor_section.py  # 모니터링 섹션
│       ├── server_section.py   # 서버 관리 섹션
│       ├── settings_dialog.py  # 설정 다이얼로그
│       └── popups/ # 팝업 다이얼로그
└── utils/          # 유틸리티 함수
    ├── async_utils.py        # 비동기 처리
    └── server_utils.py       # 서버 유틸리티
```

## 설치 방법

### 1. 시스템 요구사항
- Python 3.12 이상
- pip 패키지 관리자
- 운영체제: Windows 10/11, macOS, Linux

### 2. 의존성 설치
```bash
pip3 install -r requirements.txt
```

### 3. 환경 설정
1. 환경 변수 설정
   - `.env` 파일 생성
   ```
   LOG_LEVEL=INFO
   LOG_FILE=app.log
   CONFIG_FILE=config/app_config.json
   ```

2. 애플리케이션 설정
   - `config/app_config.json` 파일에서 기본 설정 구성
   ```json
   {
     "refresh_interval": 30,
     "max_servers": 100,
     "log_retention_days": 30,
     "default_port": 443
   }
   ```

### 4. 실행 방법
```bash
python3 main.py
```

## 사용 방법

### 1. 서버 등록
1. 서버 정보 입력:
   - 서버 이름
   - IP 주소
   - 사용자 이름
   - 비밀번호
3. "추가" 버튼 클릭
4. 선택된 서버 클릭 혹은 더블 클릭 시 서버 연결 동작

### 2. 서버 모니터링
- 메인 화면에서 등록된 서버 목록 확인
- 서버 선택 시 상세 정보 표시
- 실시간 모니터링 데이터 확인

### 3. 이벤트 관리
- "이벤트" 탭에서 시스템 이벤트 로그 OR LC 로그 확인
- 심각도 별 색상으로 이벤트 구분

## 문제 해결

### 일반적인 문제
1. 연결 오류
   - 서버 IP 주소 확인
   - iDRAC 포트(기본 443) 확인
   - 네트워크 연결 상태 확인

2. 인증 오류
   - 사용자 이름과 비밀번호 재확인
   - iDRAC 계정 잠금 여부 확인

## 로그 관리
- 로그 파일 위치: `dell_logging/app.log`
- 로그 레벨: Debug (기본값)
- 로그 보관 기간: 별도로 없음.
- 로그 포맷: `시간 [로그레벨] 메시지`

## 보안 고려사항
- 모든 비밀번호는 암호화되어 저장
- HTTPS 통신만 사용
- 세션 타임아웃 적용
- 로그에 민감정보 미포함

## 업데이트 예정
- TSR LOG 수집 기능 구현 (예정)
- 다중 서버 관리 기능 구현 (예정)

## 업데이트 내역
### v1.0.0 (2024-12-18)
- 최초 릴리즈
- 각 모니터링 기능 구현
- 서버 관리 기능 구현
- UI 개선 및 안정화

## 업데이트 내역
### v1.1.0 (2024-12-21)
- 모니터링 이벤트 방식 Redfish API 구독 방식 추가

## 업데이트 내역
### v1.2.0 (2024-12-22)
- 현재 HW Rebuilding 단독 확인 기능에서 여러 Rebuilding 볼 수 있도록 반영
- 시스템 상태 / Rebuilding 버튼 클릭 / 엑셀 저장 시 디스크 이름 (Disk.Bay.X) 간소화

## 업데이트 내역
### v1.3.0 (2024-12-23)
- 시스템 이벤트 로그 관리 기능 개선 (LifeCycle Event 최신으로 가져오게 개선)
- SSH 버튼 기능 추가 (호스트네임 조회, 호스트네임 변경 (초기화 포함), SEL 로그 초기화) 업데이트