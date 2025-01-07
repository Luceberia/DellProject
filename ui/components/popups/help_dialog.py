from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, 
                           QWidget, QTextBrowser, QPushButton, QHBoxLayout)

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dell Server Management Help")
        self.setMinimumSize(600, 400)
        
        # 메인 레이아웃
        layout = QVBoxLayout()
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 기본 사용법 탭
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        basic_text = QTextBrowser()
        basic_text.setOpenExternalLinks(True)
        basic_text.setHtml(self._get_basic_usage_text())
        basic_layout.addWidget(basic_text)
        basic_tab.setLayout(basic_layout)
        
        # 상세 기능 탭
        features_tab = QWidget()
        features_layout = QVBoxLayout()
        features_text = QTextBrowser()
        features_text.setOpenExternalLinks(True)
        features_text.setHtml(self._get_features_text())
        features_layout.addWidget(features_text)
        features_tab.setLayout(features_layout)
        
        # 문제 해결 탭
        troubleshoot_tab = QWidget()
        troubleshoot_layout = QVBoxLayout()
        troubleshoot_text = QTextBrowser()
        troubleshoot_text.setOpenExternalLinks(True)
        troubleshoot_text.setHtml(self._get_troubleshooting_text())
        troubleshoot_layout.addWidget(troubleshoot_text)
        troubleshoot_tab.setLayout(troubleshoot_layout)
        
        # 탭 추가
        tab_widget.addTab(basic_tab, "기본 사용법")
        tab_widget.addTab(features_tab, "상세 기능")
        tab_widget.addTab(troubleshoot_tab, "문제 해결")
        
        # 레이아웃에 탭 위젯 추가
        layout.addWidget(tab_widget)
        
        # 닫기 버튼
        button_layout = QHBoxLayout()
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def _get_basic_usage_text(self):
        return """
        <h2>Dell iDRAC Monitor 기본 사용법</h2>
        <p>Dell iDRAC Monitor는 Dell 서버의 원격 관리 및 모니터링을 위한 애플리케이션입니다.</p>
        
        <h3>🖥️ 서버 연결</h3>
        <ul>
            <li>메인 화면에서 서버 목록 선택</li>
            <li>'연결' 버튼을 클릭하여 서버에 연결</li>
            <li>연결된 서버의 상태, 로그, 시스템 정보 실시간 모니터링</li>
        </ul>
        
        <h3>⚙️ 주요 기능</h3>
        <ul>
            <li>Redfish API를 통한 서버 상태 실시간 모니터링</li>
            <li>서버 연결 상태 및 성능 추적</li>
            <li>SEL(시스템 이벤트 로그) 확인</li>
            <li>서버 연결 상태에 따른 자동 폴링 간격 조정</li>
        </ul>
        
        <h3>🔒 보안 및 연결</h3>
        <ul>
            <li>SSL 인증서 검증 비활성화 (개발/테스트 환경)</li>
            <li>3초 타임아웃 설정</li>
            <li>캐시 메커니즘을 통한 성능 최적화</li>
        </ul>
        """

    def _get_features_text(self):
        return """
        <h2>Dell iDRAC Monitor 상세 기능</h2>
        
        <h3>🔍 서버 연결 관리</h3>
        <ul>
            <li><strong>연결 상태 모니터링</strong>: 실시간 서버 연결 상태 추적</li>
            <li><strong>자동 재연결</strong>: 연결 실패 시 최대 3회 재시도</li>
            <li><strong>동적 폴링 간격</strong>: 서버 응답 시간에 따라 폴링 간격 자동 조정 (5-60초)</li>
        </ul>
        
        <h3>📊 시스템 정보 모니터링</h3>
        <ul>
            <li><strong>시스템 상태</strong>: 서버 하드웨어, 온도, 전원 상태 확인</li>
            <li><strong>이벤트 로그</strong>: SEL(시스템 이벤트 로그) 실시간 모니터링</li>
            <li><strong>성능 메트릭</strong>: 응답 시간, 연결 상태 추적</li>
        </ul>
        
        <h3>🔔 알림 및 이벤트</h3>
        <ul>
            <li><strong>이벤트 구독</strong>: Redfish API 이벤트 서비스 지원</li>
            <li><strong>로그 알림</strong>: 새로운 시스템 이벤트 로그 발생 시 알림</li>
            <li><strong>연결 상태 변경 알림</strong>: 서버 연결/해제 시 UI 상태 자동 업데이트</li>
        </ul>
        
        <h3>🗃️ 데이터 관리</h3>
        <ul>
            <li><strong>캐시 메커니즘</strong>: 최대 100개 항목, 5분 TTL</li>
            <li><strong>세션 관리</strong>: 서버별 개별 세션 추적</li>
            <li><strong>로깅</strong>: 애플리케이션 및 서버 활동 로그 기록</li>
        </ul>
        """

    def _get_troubleshooting_text(self):
        return """
        <h2>문제 해결 가이드</h2>
        
        <h3>🚨 일반적인 문제</h3>
        <ul>
            <li><strong>서버 연결 실패</strong>
                <ul>
                    <li>네트워크 연결 확인</li>
                    <li>서버 IP, 포트, 인증 정보 재확인</li>
                    <li>방화벽 설정 점검</li>
                </ul>
            </li>
            <li><strong>SSL/인증서 문제</strong>
                <ul>
                    <li>현재 SSL 인증서 검증 비활성화됨</li>
                    <li>프로덕션 환경에서는 인증서 검증 권장</li>
                </ul>
            </li>
        </ul>
        
        <h3>🔍 로그 확인</h3>
        <ul>
            <li><strong>애플리케이션 로그</strong>: `resources/logs/app.log`</li>
            <li><strong>로그 레벨</strong>: WARNING, ERROR, INFO 등 다양한 로그 레벨 지원</li>
        </ul>
        
        <h3>🛠️ 성능 문제</h3>
        <ul>
            <li><strong>느린 응답</strong>
                <ul>
                    <li>네트워크 대역폭 확인</li>
                    <li>서버 부하 모니터링</li>
                    <li>폴링 간격 조정 (5-60초)</li>
                </ul>
            </li>
            <li><strong>메모리 사용량</strong>
                <ul>
                    <li>캐시 크기 제한 (최대 100개 항목)</li>
                    <li>불필요한 세션 정리</li>
                </ul>
            </li>
        </ul>
        
        <h3>📞 추가 지원</h3>
        <ul>
            <li>GitHub 이슈 트래커에 버그 및 기능 요청 가능
                <ul>
                    <li><a href="https://github.com/Luceberia/DellProject/issues">GitHub 이슈 트래커 바로가기</a></li>
                </ul>
            </li>
            <li>프로젝트 GitHub 저장소
                <ul>
                    <li><a href="https://github.com/Luceberia/DellProject/releases/latest">DellProject GitHub 저장소</a></li>
                </ul>
        </ul>
        """