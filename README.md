# Dell iDRAC Monitor

## 개요
Dell iDRAC Monitor는 Dell 서버의 원격 관리 및 모니터링을 위한 PyQt6 기반 데스크톱 애플리케이션입니다.

## 주요 기능
- Redfish API를 통한 Dell 서버 상태 모니터링
- 서버 연결 및 정보 조회
- 실시간 서버 상태 추적
- 안전한 네트워크 연결 관리

## 디렉토리 구조
- `common/`: 공통 유틸리티 및 데이터 관리
- `config/`: 시스템 및 서버 설정 관리
- `endpoints/`: Redfish API 엔드포인트 관리
- `error/`: 에러 처리 핸들러
- `managers/`: 서버 관리 핵심 로직
- `network/`: 네트워크 연결 관리
- `ui/`: 사용자 인터페이스 모듈
- `utils/`: 다양한 유틸리티 함수

## 요구사항
- Python 3.12.8
- 주요 의존성 라이브러리:
  - PyQt6 (6.6.1): GUI 프레임워크
  - requests (2.31.0): HTTP 요청 라이브러리
  - urllib3 (2.2.3): HTTP 클라이언트
  - pandas (2.2.3): 데이터 처리
  - psutil (6.1.1): 시스템 모니터링
  - python-dotenv (1.0.0): 환경 변수 관리

## 개발 환경 설정
1. 가상 환경 생성
```bash
python3.12 -m venv venv
source venv/bin/activate
```

2. 의존성 설치
```bash
pip3 install -r requirements.txt
```

## 주요 모듈 설명
- `main.py`: 애플리케이션 진입점, 리소스 초기화 및 로깅 설정
- `managers/dell_server_manager.py`: Dell 서버 관리 및 Redfish API 상호작용
- `endpoints/redfish_endpoints.py`: Redfish API 엔드포인트 정의
- `ui/main_window.py`: 메인 사용자 인터페이스 구현

## 로깅
- 로그 파일 위치: `resources/logs/app.log`
- 로깅 설정: `config/system/log_config.py`

## 보안 및 연결
- SSL 인증서 검증 비활성화 (개발/테스트 환경)
- 타임아웃 3초 설정
- 캐시 메커니즘을 통한 성능 최적화

## 문제 해결
- 네트워크 연결 문제 발생 시 `network/connection_manager.py` 확인
- API 엔드포인트 오류는 `endpoints/redfish_endpoints.py` 참조

## 빌드 및 배포
- PyInstaller를 사용한 애플리케이션 패키징
- macOS 애플리케이션 번들 생성 지원

## 라이선스
[라이선스 정보 추가 예정]
