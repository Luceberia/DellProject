import os
from functools import lru_cache
import time

import requests
import urllib3

from config.system.log_config import setup_logging
from endpoints.redfish_endpoints import RedfishEndpoints, URLPattern

# logger 객체 생성
logger = setup_logging()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DellServerManager:
    def __init__(self, ip: str, port: str, auth: tuple):
        self.endpoints = RedfishEndpoints(ip, port)
        self.auth = auth
        self.timeout = 3  # 타임아웃을 3초로 줄임
        self.session = requests.Session()
        self.session.verify = False
        self.cache = {}
        self.cache_ttl = 300  # 5분
        self.last_etag = {}
        self.redfish_client = None  # Redfish 클라이언트 초기화

    def check_connection(self):
        """서버와의 기본 연결 상태 확인"""
        try:
            response = self.session.get(
                f"{self.endpoints.base_url}/redfish/v1", 
                auth=self.auth,
                verify=False,
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"서버 연결 확인 실패: {str(e)}")
            return False

    def clear_session(self):
        """세션 및 캐시 초기화"""
        self.session = requests.Session()
        self.session.verify = False
        self.cache.clear()
        self.last_etag.clear()
        self.redfish_client = None

    @lru_cache(maxsize=32)        
    def fetch_basic_info(self):
        """시스템 기본 정보 조회"""
        # 먼저 기본 연결 상태 확인
        if not self.check_connection():
            raise requests.exceptions.ConnectionError("서버와 연결할 수 없습니다.")
            
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                responses = {
                    'system': self.session.get(self.endpoints.system, auth=self.auth, verify=False, timeout=self.timeout),
                    'bios': self.session.get(self.endpoints.bios, auth=self.auth, verify=False, timeout=self.timeout),
                    'idrac': self.session.get(self.endpoints.managers, auth=self.auth, verify=False, timeout=self.timeout)
                }
                
                for response in responses.values():
                    response.raise_for_status()
                
                system_info = responses['system'].json()
                bios_info = responses['bios'].json()
                idrac_info = responses['idrac'].json()
                
                service_tag = system_info.get('SKU', 'None')
                
                return {
                    'system': {
                        **system_info,
                        'ServiceTag': service_tag
                    },
                    'bios': bios_info,
                    'idrac': idrac_info
                }
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"연결 시도 {attempt + 1}/{max_retries} 실패: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"최대 재시도 횟수 초과: {str(e)}")
                    raise

    def get_cached_data(self, key, fetch_func):
        if key not in self.cache or time.time() - self.cache[key]['timestamp'] > self.cache_ttl:
            self.cache[key] = {
                'data': fetch_func(),
                'timestamp': time.time()
            }
        return self.cache[key]['data']

    def fetch_system_info(self):
        return self.get_cached_data('system_info', self.fetch_basic_info)

    def fetch_differential_update(self, endpoint):
        headers = {'If-None-Match': self.last_etag.get(endpoint, '')}
        response = self.session.get(endpoint, auth=self.auth, headers=headers, verify=False)
        if response.status_code == 304:  # Not Modified
            return None
        self.last_etag[endpoint] = response.headers.get('ETag', '')
        return response.json()

    def fetch_system_info_differential(self):
        return self.fetch_differential_update(self.endpoints.system)

    def fetch_bios_info(self):
        """BIOS 상세 정보 조회"""
        return self.fetch_detailed_info(self.endpoints.bios)

    def fetch_idrac_info(self):
        """iDRAC 상세 정보 조회"""
        return self.fetch_detailed_info(self.endpoints.idrac_info)

    def fetch_idrac_pwr_info(self):
        """iDRAC PWR 상세 정보 조회"""
        return self.fetch_detailed_info(self.endpoints.idrac_pwr_info)

    def fetch_idrac_mac_address(self):
        """iDRAC MAC 주소 조회"""
        try:
            idrac_info = self.fetch_detailed_info(self.endpoints.idrac_mac_address)
            return idrac_info.get('Attributes', {}).get('CurrentNIC.1.MACAddress')
        except Exception as e:
            logger.error(f"iDRAC MAC 주소 조회 실패: {str(e)}")
            return None

    def check_idrac_license(self):
        """iDRAC 라이선스 정보 조회"""
        try:
            license_data = self.fetch_detailed_info(self.endpoints.license_info)
            
            if license_data.get('Members', []):
                license_detail = license_data['Members'][0]
                return {
                    'type': license_detail.get('LicenseDescription', ['Unknown'])[0],
                    'status': license_detail.get('LicensePrimaryStatus'),
                    'license_type': license_detail.get('LicenseType'),
                    'install_date': license_detail.get('LicenseInstallDate')
                }
            return None
        except Exception as e:
            logger.error(f"라이선스 정보 조회 실패: {str(e)}")
            return None

    def fetch_detailed_info(self, endpoint):
        """공통 상세 정보 조회 메서드"""
        try:
            response = requests.get(endpoint, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"상세 정보 조회 실패: {e}")
            raise

    def fetch_processors_info(self):
        """CPU 상세 정보 조회"""
        return self.fetch_detailed_info(self.endpoints.processors)

    def fetch_memory_info(self):
        """메모리 상세 정보 조회"""
        return self.fetch_detailed_info(self.endpoints.memory)

    def fetch_storage_info(self):
        """스토리지 상세 정보 조회"""
        try:
            response = requests.get(
                f"{self.endpoints.storage}",
                auth=self.auth,
                verify=False
            )
            response.raise_for_status()
            storage_data = response.json()
            
            result = []
            for member in storage_data.get('Members', []):
                member_uri = member.get('@odata.id')
                if member_uri:
                    # 컨트롤러 정보 조회
                    controller_response = requests.get(
                        f"{self.endpoints.base_url}{member_uri}",
                        auth=self.auth,
                        verify=False
                    )
                    controller_data = controller_response.json()
                    
                    # 볼륨 정보 조회
                    volumes = []
                    volumes_uri = f"{self.endpoints.base_url}{member_uri}/Volumes"
                    volumes_response = requests.get(
                        volumes_uri,
                        auth=self.auth,
                        verify=False
                    )
                    if volumes_response.status_code == 200:
                        volumes_data = volumes_response.json()
                        for volume in volumes_data.get('Members', []):
                            volume_uri = volume.get('@odata.id')
                            if volume_uri:
                                volume_response = requests.get(
                                    f"{self.endpoints.base_url}{volume_uri}",
                                    auth=self.auth,
                                    verify=False
                                )
                                volumes.append(volume_response.json())
                    
                    controller_data['Volumes'] = volumes
                    
                    # 드라이브 정보 조회 (기존 코드와 동일)
                    drives = []
                    for drive in controller_data.get('Drives', []):
                        drive_uri = drive.get('@odata.id')
                        if drive_uri:
                            drive_response = requests.get(
                                f"{self.endpoints.base_url}{drive_uri}",
                                auth=self.auth,
                                verify=False
                            )
                            drives.append(drive_response.json())
                    
                    controller_data['Drives'] = drives
                    result.append(controller_data)
            
            return {'Controllers': result}
        except Exception as e:
            logger.error(f"스토리지 정보 조회 실패: {str(e)}")
            return None

    def fetch_storage_detail(self, storage_id):
        """스토리지 컨트롤러 상세 정보 조회"""
        try:
            # storage_id가 전체 경로를 포함하고 있는 경우
            if storage_id.startswith('/redfish'):
                url = f"{self.endpoints.base_url}{storage_id}"
            else:
                # storage_id가 컨트롤러 ID만 포함하는 경우
                url = f"{self.endpoints.storage}/{storage_id}"
                
            response = requests.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"스토리지 상세 정보 조회 실패: {e}")
            return None

    def fetch_drives_info(self, controller_id):
        """특정 컨트롤러의 드라이브 목록 조회"""
        try:
            url = self.endpoints.get_storage_drives_url(controller_id)
            response = requests.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"드라이브 목록 조회 실패: {e}")
            return None

    def fetch_drive_detail(self, controller_id, drive_id):
        """개별 드라이브 상세 정보 조회"""
        try:
            # 전체 URL 경로를 사용하도록 수정
            url = f"{self.endpoints.storage}/{controller_id}/Drives/{drive_id}"
            response = requests.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"드라이브 상세 정보 조회 실패: {e}")
            return None

    def fetch_drive_rebuild_status(self, drive):
        try:
            drive_uri = drive.get('@odata.id')
            if drive_uri:
                response = requests.get(
                    f"{self.endpoints.base_url}{drive_uri}",
                    auth=self.auth,
                    verify=False
                )
                return response.json()
        except Exception as e:
            logger.error(f"드라이브 리빌딩 상태 조회 실패: {str(e)}")
        return None

    def fetch_network_adapters_info(self):
        """네트워크 어댑터 정보 조회"""
        try:
            # 네트워크 어댑터 목록 조회
            response = requests.get(self.endpoints.network_adapters, auth=self.auth, verify=False)
            response.raise_for_status()
            adapters_data = response.json()

            result = []
            for adapter in adapters_data.get('Members', []):
                adapter_uri = adapter.get('@odata.id')
                if adapter_uri:
                    # 어댑터 상세 정보 조회
                    adapter_response = requests.get(
                        f"{self.endpoints.base_url}{adapter_uri}",
                        auth=self.auth,
                        verify=False
                    )
                    adapter_response.raise_for_status()
                    adapter_info = adapter_response.json()

                    # 포트 정보 조회
                    ports = []
                    ports_uri = adapter_info.get('NetworkPorts', {}).get('@odata.id')
                    if ports_uri:
                        ports_response = requests.get(
                            f"{self.endpoints.base_url}{ports_uri}",
                            auth=self.auth,
                            verify=False
                        )
                        ports_response.raise_for_status()
                        ports_data = ports_response.json()
                        for port in ports_data.get('Members', []):
                            port_uri = port.get('@odata.id')
                            if port_uri:
                                port_response = requests.get(
                                    f"{self.endpoints.base_url}{port_uri}",
                                    auth=self.auth,
                                    verify=False
                                )
                                port_response.raise_for_status()
                                ports.append(port_response.json())

                    # 네트워크 장치 기능 정보 조회
                    device_functions = []
                    device_functions_uri = adapter_info.get('NetworkDeviceFunctions', {}).get('@odata.id')
                    if device_functions_uri:
                        functions_response = requests.get(
                            f"{self.endpoints.base_url}{device_functions_uri}",
                            auth=self.auth,
                            verify=False
                        )
                        functions_response.raise_for_status()
                        functions_data = functions_response.json()
                        
                        for function in functions_data.get('Members', []):
                            function_uri = function.get('@odata.id')
                            if function_uri:
                                function_response = requests.get(
                                    f"{self.endpoints.base_url}{function_uri}",
                                    auth=self.auth,
                                    verify=False
                                )
                                function_response.raise_for_status()
                                device_functions.append(function_response.json())

                    # 결과에 추가
                    adapter_info['NetworkPorts'] = ports
                    adapter_info['NetworkDeviceFunctions'] = device_functions
                    result.append(adapter_info)

            return {'NetworkAdapters': result}
        except Exception as e:
            logger.error(f"네트워크 어댑터 정보 조회 실패: {str(e)}")
            raise

    def fetch_psu_info(self):
        """PSU 상세 정보 조회"""
        return self.fetch_detailed_info(self.endpoints.get_url(URLPattern.CHASSIS_POWER))

    def fetch_gpu_info(self):
        """GPU 정보 조회"""
        try:
            result = []
            
            try:

                # 1. 프로세서에서 내장 GPU 확인
                processors_response = requests.get(
                    self.endpoints.processors,
                    auth=self.auth,
                    verify=False
                )
                processors_response.raise_for_status()
                processors_data = processors_response.json()
                
                # 프로세서 정보 상세 조회
                for processor in processors_data.get('Members', []):
                    processor_uri = processor.get('@odata.id')
                    if processor_uri:
                        processor_response = requests.get(
                            f"{self.endpoints.base_url}{processor_uri}",
                            auth=self.auth,
                            verify=False
                        )
                        processor_response.raise_for_status()
                        processor_info = processor_response.json()
                        
                        # 내장 GPU 확인
                        if processor_info.get('ProcessorType') == 'CPU' and \
                        'Graphics' in processor_info.get('ProcessorCharacteristics', []):
                            result.append({
                                'Type': 'Integrated',
                                'Name': f"내장 GPU ({processor_info.get('Model', 'N/A')})",
                                'Manufacturer': processor_info.get('Manufacturer', 'N/A'),
                                'Status': processor_info.get('Status', {}),
                                'ProcessorInfo': processor_info
                            })
            except requests.exceptions.RequestException as e:
                logger.info(f"프로세서 정보 조회 중 오류 발생: {str(e)}")
                processors_data = {'Members': []}
            try: 
                # 2. PCIe 장치에서 독립 GPU 확인
                pcie_response = requests.get(
                    self.endpoints.pcie_devices,
                    auth=self.auth,
                    verify=False
                )
                pcie_response.raise_for_status()
                pcie_devices = pcie_response.json()
                
                # PCIe 장치 상세 정보 조회
                for device in pcie_devices.get('Members', []):
                    device_uri = device.get('@odata.id')
                    if device_uri:
                        device_response = requests.get(
                            f"{self.endpoints.base_url}{device_uri}",
                            auth=self.auth,
                            verify=False
                        )
                        device_response.raise_for_status()
                        device_info = device_response.json()
                        
                        # PCIe 기능 정보 조회
                        functions = []
                        functions_uri = device_info.get('PCIeFunctions', {}).get('@odata.id')
                        if functions_uri:
                            functions_response = requests.get(
                                f"{self.endpoints.base_url}{functions_uri}",
                                auth=self.auth,
                                verify=False
                            )
                            functions_response.raise_for_status()
                            functions_data = functions_response.json()
                            
                            for function in functions_data.get('Members', []):
                                function_uri = function.get('@odata.id')
                                if function_uri:
                                    function_response = requests.get(
                                        f"{self.endpoints.base_url}{function_uri}",
                                        auth=self.auth,
                                        verify=False
                                    )
                                    function_response.raise_for_status()
                                    functions.append(function_response.json())

                        # GPU 장치 식별 및 결과 추가
                        if device_info.get('DeviceType', '').upper() in ['GPU', 'VGA'] or \
                        device_info.get('ClassCode', '').startswith('0x03'):
                            device_info['PCIeFunctions'] = functions
                            result.append({
                                'Type': 'Discrete',
                                'Name': device_info.get('Name', 'N/A'),
                                'Manufacturer': device_info.get('Manufacturer', 'N/A'),
                                'Model': device_info.get('Model', 'N/A'),
                                'Status': device_info.get('Status', {}),
                                'DeviceInfo': device_info,
                                'Oem': device_info.get('Oem', {})
                            })
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logger.info("PCIe 장치 정보를 지원하지 않는 시스템입니다.")
                else:
                    logger.error(f"PCIe 장치 정보 조회 중 오류 발생: {str(e)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"PCIe 장치 정보 조회 중 오류 발생: {str(e)}")
            
            return {'GPUDevices': result}
            
        except Exception as e:
            logger.error(f"GPU 정보 조회 중 오류 발생: {str(e)}")
            return {'GPUDevices': []}

    def fetch_sel_entries(self, progress_callback=None, limit=300):
        """SEL 로그 엔트리 조회"""
        try:
            all_entries = []
            response = self.session.get(self.endpoints.sel_entries, auth=self.auth, verify=False)
            response.raise_for_status()
            data = response.json()
            
            total_count = data.get('Members@odata.count', 0)
            if total_count == 0:
                return {'Members': [], 'TotalCount': 0}
                
            start_id = total_count
            entries_found = 0
            
            while entries_found < limit and start_id > 0:
                entry_url = f"{self.endpoints.sel_entries}/{start_id}"
                
                try:
                    response = self.session.get(entry_url, auth=self.auth, verify=False)
                    response.raise_for_status()
                    entry_data = response.json()
                    all_entries.append(entry_data)
                    entries_found += 1
                    
                    if progress_callback:
                        progress = min((entries_found / limit) * 100, 100)
                        progress_callback(progress)
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code != 404:
                        raise
                        
                start_id -= 1
            
            sorted_entries = sorted(all_entries, 
                                key=lambda x: x.get('Created', ''), 
                                reverse=True)
            
            if progress_callback:
                progress_callback(100)
                
            return {'Members': sorted_entries[:limit], 'TotalCount': len(sorted_entries)}
            
        except Exception as e:
            logger.error(f"SEL 로그 엔트리 조회 실패: {str(e)}")
            return {'Members': []}

    def fetch_lc_entries(self, progress_callback=None, limit=300):
        """LC 로그 엔트리 조회"""
        try:
            all_entries = []
            response = self.session.get(self.endpoints.lc_entries, auth=self.auth, verify=False)
            response.raise_for_status()
            data = response.json()
            
            total_count = data.get('Members@odata.count', 0)
            if total_count == 0:
                return {'Members': [], 'TotalCount': 0}
                
            start_id = total_count
            entries_found = 0
            
            while entries_found < limit and start_id > 0:
                entry_url = f"{self.endpoints.lc_entries}/{start_id}"
                
                try:
                    response = self.session.get(entry_url, auth=self.auth, verify=False)
                    response.raise_for_status()
                    entry_data = response.json()
                    all_entries.append(entry_data)
                    entries_found += 1
                    
                    if progress_callback:
                        progress = min((entries_found / limit) * 100, 100)
                        progress_callback(progress)
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code != 404:
                        raise
                        
                start_id -= 1
            
            sorted_entries = sorted(all_entries, 
                                key=lambda x: x.get('Created', ''), 
                                reverse=True)
            
            if progress_callback:
                progress_callback(100)
                
            return {'Members': sorted_entries[:limit], 'TotalCount': len(sorted_entries)}
            
        except Exception as e:
            logger.error(f"LC 로그 엔트리 조회 실패: {str(e)}")
            return {'Members': []}

    def clear_sel_logs(self):
        """SEL 로그 클리어"""
        try:
            response = self.session.post(
                self.endpoints.clear_sel_log,
                headers={'Content-Type': 'application/json'},
                json={},  # 빈 JSON 객체 전송
                auth=self.auth,
                verify=False
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"SEL 로그 클리어 실패: {str(e)}")
            raise

    def fetch_sel_service(self):
        """SEL 로그 서비스 정보 조회"""
        try:
            response = self.session.get(self.endpoints.sel_log_service, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SEL 로그 서비스 정보 조회 실패: {str(e)}")
            raise

    def fetch_lc_service(self):
        """LC 로그 서비스 정보 조회"""
        try:
            response = self.session.get(self.endpoints.lc_log_service, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"LC 로그 서비스 정보 조회 실패: {str(e)}")
            raise

    def fetch_firmware_inventory(self):
        """펌웨어 인벤토리 정보 조회"""
        try:
            response = self.session.get(
                self.endpoints.firmware_inventory,
                auth=self.auth,
                verify=False,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"펌웨어 인벤토리 조회 실패: {str(e)}")
            return None

    def update_firmware(self, file_path: str = None, image_uri: str = None, transfer_protocol: str = "HTTP"):
        """펌웨어 업데이트를 시작합니다."""
        try:
            if file_path and os.path.exists(file_path):
                # 파일 정보 로깅
                file_size = os.path.getsize(file_path)
                _, ext = os.path.splitext(file_path)
                logger.debug(f"[펌웨어 업데이트] 파일 정보:")
                logger.debug(f" - 파일 경로: {file_path}")
                logger.debug(f" - 파일 크기: {file_size} bytes")
                logger.debug(f" - 파일 형식: {ext}")
                
                if ext.lower() not in ['.exe', '.d7', '.d8', '.d9', '.pm', '.sc']:
                    logger.error(f"지원되지 않는 파일 형식입니다: {ext}")
                    return None

                # Dell Update Service Install 엔드포인트 사용
                import base64
                with open(file_path, 'rb') as f:
                    encoded = base64.b64encode(f.read()).decode()
                
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Auth-Token': self.auth[1] if isinstance(self.auth, tuple) else None
                }
                
                payload = {
                    "SoftwareIdentityURIs": [],  # 펌웨어 ID 목록 (선택사항)
                    "ShareParameters": {
                        "Target": "ALL",  # 모든 구성 요소 업데이트
                        "IPAddress": "",  # 로컬 업데이트이므로 비워둠
                        "ShareName": "",
                        "UserName": "",
                        "Password": ""
                    },
                    "ImageFile": encoded,
                    "ImportOptions": "Include"  # 모든 구성 요소 포함
                }
                
                # 요청 정보 로깅
                logger.debug(f"[펌웨어 업데이트] Dell Update Service 요청 정보:")
                logger.debug(f" - URL: {self.endpoints.firmware_rollback}")  # firmware_rollback이 DellUpdateService.Install 엔드포인트
                logger.debug(f" - 헤더: {headers}")
                logger.debug(f" - 파일명: {os.path.basename(file_path)}")
                logger.debug(f" - Payload 크기: {len(encoded)} bytes")
                
                response = self.session.post(
                    self.endpoints.firmware_rollback,  # DellUpdateService.Install 엔드포인트 사용
                    auth=self.auth,
                    verify=False,
                    json=payload,
                    headers=headers,
                    timeout=300
                )
                
                # 응답 정보 로깅
                logger.debug(f"[펌웨어 업데이트] 응답 정보:")
                logger.debug(f" - 상태 코드: {response.status_code}")
                logger.debug(f" - 응답 헤더: {dict(response.headers)}")
                logger.debug(f" - 응답 내용: {response.text}")
                
                response.raise_for_status()
                return response.json()
                    
            elif image_uri:
                # 원격 URI를 통한 업데이트는 SimpleUpdate 사용
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                payload = {
                    "ImageURI": image_uri,
                    "TransferProtocol": transfer_protocol
                }
                
                # 원격 URI 요청 정보 로깅
                logger.debug(f"[펌웨어 업데이트] 원격 URI 요청 정보:")
                logger.debug(f" - URL: {self.endpoints.firmware_update}")
                logger.debug(f" - 헤더: {headers}")
                logger.debug(f" - Payload: {payload}")
                
                response = self.session.post(
                    self.endpoints.firmware_update,
                    auth=self.auth,
                    verify=False,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # 원격 URI 응답 정보 로깅
                logger.debug(f"[펌웨어 업데이트] 원격 URI 응답 정보:")
                logger.debug(f" - 상태 코드: {response.status_code}")
                logger.debug(f" - 응답 헤더: {dict(response.headers)}")
                logger.debug(f" - 응답 내용: {response.text}")
                
                response.raise_for_status()
                return response.json()
            else:
                raise ValueError("file_path 또는 image_uri 중 하나는 반드시 제공되어야 합니다.")
            
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                status_code = e.response.status_code
                error_message = str(e.response.text) if hasattr(e.response, 'text') else str(e)
                
                # 에러 상세 정보 로깅
                logger.debug(f"[펌웨어 업데이트] 에러 상세 정보:")
                logger.debug(f" - 상태 코드: {status_code}")
                logger.debug(f" - 에러 메시지: {error_message}")
                logger.debug(f" - 요청 URL: {e.response.url}")
                logger.debug(f" - 요청 메소드: {e.response.request.method}")
                logger.debug(f" - 요청 헤더: {dict(e.response.request.headers)}")
                if hasattr(e.response.request, 'body'):
                    logger.debug(f" - 요청 본문: {e.response.request.body}")
                
                if status_code == 404:
                    logger.error(f"펌웨어 업데이트 엔드포인트를 찾을 수 없습니다. iDRAC 버전을 확인해주세요.\n상세 오류: {error_message}")
                elif status_code == 400:
                    logger.error(f"잘못된 요청입니다. 펌웨어 파일이나 URI가 올바른지 확인해주세요.\n상세 오류: {error_message}")
                else:
                    logger.error(f"펌웨어 업데이트 실패 (상태 코드: {status_code}): {error_message}")
            else:
                logger.error(f"펌웨어 업데이트 실패: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"예기치 않은 오류 발생: {str(e)}")
            logger.debug(f"[펌웨어 업데이트] 예외 정보:", exc_info=True)
            return None

    def rollback_firmware(self, component_id: str):
        """펌웨어 롤백 실행
        
        Args:
            component_id (str): 롤백할 컴포넌트 ID
        """
        try:
            payload = {
                "ComponentID": component_id,
                "InstallOption": "Previous"
            }
            response = self.session.post(
                self.endpoints.firmware_rollback,
                auth=self.auth,
                verify=False,
                timeout=self.timeout,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"펌웨어 롤백 실행 실패: {str(e)}")
            return None

    def multipart_firmware_update(self, file_path):
        """대용량 펌웨어 파일을 업데이트합니다.
        이 메소드는 더 이상 멀티파트 업로드를 시도하지 않고, 
        대신 update_firmware 메소드를 호출합니다.
        """
        if isinstance(file_path, list):
            results = []
            for single_file in file_path:
                result = self.update_firmware(file_path=single_file)
                results.append(result)
            return results
        else:
            return self.update_firmware(file_path=file_path)

    def get_firmware_queue(self):
        """펌웨어 업데이트 대기열 조회"""
        try:
            # 먼저 기본 Jobs 엔드포인트 시도
            try:
                response = self.session.get(
                    self.endpoints.firmware_queue,
                    auth=self.auth,
                    verify=False,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if e.response and e.response.status_code == 404:
                    # 대체 엔드포인트 시도
                    alt_endpoints = [
                        f"{self.endpoints.base_url}/redfish/v1/Managers/iDRAC.Embedded.1/Jobs",
                        f"{self.endpoints.base_url}/redfish/v1/JobService/Jobs",
                        f"{self.endpoints.base_url}/redfish/v1/TaskService/Tasks"
                    ]
                    
                    for endpoint in alt_endpoints:
                        try:
                            response = self.session.get(
                                endpoint,
                                auth=self.auth,
                                verify=False,
                                timeout=self.timeout
                            )
                            response.raise_for_status()
                            return response.json()
                        except:
                            continue
                    
                    logger.error("펌웨어 대기열 조회 실패. 지원되는 Jobs 엔드포인트를 찾을 수 없습니다.")
                    return None
                else:
                    raise
        except requests.exceptions.RequestException as e:
            logger.error(f"펌웨어 대기열 조회 실패: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"예기치 않은 오류 발생: {str(e)}")
            return None

    def get_firmware_settings(self):
        """펌웨어 업데이트 설정 조회"""
        try:
            response = self.session.get(
                self.endpoints.firmware_settings,
                auth=self.auth,
                verify=False,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"펌웨어 설정 조회 실패: {str(e)}")
            return None

    def update_firmware_settings(self, settings: dict):
        """펌웨어 업데이트 설정 변경
        
        Args:
            settings (dict): 변경할 설정 정보
        """
        try:
            response = self.session.patch(
                self.endpoints.firmware_settings,
                auth=self.auth,
                verify=False,
                timeout=self.timeout,
                json=settings
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"펌웨어 설정 변경 실패: {str(e)}")
            return None

    def fetch_job_queue(self):
        """Job 큐 조회"""
        try:
            response = self.session.get(self.endpoints.job_collection, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Job 큐 조회 실패: {str(e)}")
            raise

    def fetch_job_details(self, job_id):
        """특정 Job 상세 정보 조회"""
        try:
            url = self.endpoints.get_job_details_url(job_id)
            response = self.session.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Job 상세 정보 조회 실패 (Job ID: {job_id}): {str(e)}")
            raise

    def delete_job(self, job_id):
        """특정 Job 삭제"""
        try:
            url = self.endpoints.get_job_details_url(job_id)
            response = self.session.delete(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Job 삭제 실패 (Job ID: {job_id}): {str(e)}")
            raise

    def collect_tsr_log(self, progress_callback=None):
        try:
            basic_info = self.fetch_basic_info()
            service_tag = basic_info['system'].get('ServiceTag', "Unknown")

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"TSR_Log_{service_tag}_{timestamp}.zip"
            
            data = {
                "ShareType": "Local",
            }
            
            logger.info(f"TSR 로그 수집 요청 시작: {filename}")
            response = requests.post(
                self.endpoints.tsr_export,
                json=data,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                verify=False
            )
            
            if response.status_code != 202:
                raise Exception(f"TSR 로그 수집 요청 실패: {response.text}")
            
            task_uri = response.headers.get('Location') or response.json().get('@odata.id')
            if not task_uri:
                raise Exception("작업 상태를 모니터링할 수 없습니다.")
            
            logger.info("TSR 로그 수집 작업 모니터링 시작")
            while True:
                task_response = requests.get(
                    f"{self.endpoints.base_url}{task_uri}",
                    auth=self.auth,
                    verify=False
                )
                
                task_data = task_response.json()
                task_state = task_data.get('TaskState')
                if task_state == 'Completed':
                    logger.info("TSR 로그 수집 완료")
                    break
                elif task_state in ['Failed', 'Exception', 'Killed']:
                    error_message = task_data.get('Messages', [{}])[0].get('Message', '알 수 없는 오류')
                    raise Exception(f"TSR 로그 수집 실패: {error_message}")
                
                time.sleep(2)
                if progress_callback:
                    progress_callback(task_data.get('PercentComplete', 0))
            
            logger.info("TSR 로그 파일 다운로드 시작")
            download_url = f"{self.endpoints.firmware_inventory}/{filename}"
            download_response = requests.get(
                download_url,
                auth=self.auth,
                verify=False,
                stream=True
            )
            
            if download_response.status_code == 200:
                download_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
                total_size = int(download_response.headers.get('content-length', 0))
                downloaded = 0
                with open(download_path, 'wb') as file:
                    for chunk in download_response.iter_content(chunk_size=8192):
                        file.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
                
                logger.info(f"TSR 로그 다운로드 완료: {download_path}")
                return download_path
            else:
                raise Exception(f"TSR 로그 다운로드 실패: HTTP 상태 코드 {download_response.status_code}")
        
        except Exception as e:
            logger.error(f"TSR 로그 수집 중 오류 발생: {str(e)}")
            return None

    def fetch_firmware_component(self, component_id: str):
        """특정 컴포넌트의 펌웨어 정보 조회"""
        try:
            response = requests.get(
                self.endpoints.get_firmware_inventory_component_url(component_id),
                auth=self.auth,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"펌웨어 컴포넌트 정보 조회 실패: {str(e)}")
            raise

    def fetch_network_virtualization_info(self, adapter_id: str, func_id: str):
        """네트워크 가상화 설정 정보 조회"""
        try:
            url = self.endpoints.get_network_adapter_attributes_url(adapter_id, func_id)
            response = requests.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"네트워크 가상화 설정 정보 조회 실패: {str(e)}")
            raise

    def fetch_all_network_settings(self, adapter_id: str, func_id: str):
        """모든 네트워크 설정 정보 조회"""
        try:
            url = self.endpoints.get_network_adapter_attributes_url(adapter_id, func_id)
            response = requests.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"네트워크 설정 조회 실패: {str(e)}")
            raise

    def update_bios_settings(self, settings: dict) -> bool:
        """
        BIOS 설정을 변경합니다.

        Args:
            settings (dict): 변경할 BIOS 설정들의 딕셔너리
                           예: {"BootMode": "Uefi", "EmbNic1": "Enabled"}

        Returns:
            bool: 설정 변경 작업이 성공적으로 큐에 추가되었는지 여부
        """
        try:
            logger.info("BIOS 설정 변경 시도")
            response = self.session.patch(
                self.endpoints.bios_settings,
                json={"Attributes": settings}
            )
            
            if response.status_code in [200, 202]:
                logger.info("BIOS 설정 변경 작업이 성공적으로 큐에 추가됨")
                return True
            else:
                logger.error(f"BIOS 설정 변경 실패. 상태 코드: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"BIOS 설정 변경 중 오류 발생: {str(e)}")
            raise

    def reset_bios(self) -> bool:
        """
        BIOS를 기본 설정으로 초기화합니다.

        Returns:
            bool: 리셋 작업이 성공적으로 큐에 추가되었는지 여부
        """
        try:
            logger.info("BIOS 리셋 시도")
            response = self.session.post(
                self.endpoints.bios_reset,
                json={},  # 빈 JSON 페이로드로 리셋 요청
                auth=self.auth,
                verify=False
            )
            
            if response.status_code in [200, 202]:
                logger.info("BIOS 리셋 작업이 성공적으로 큐에 추가됨")
                # 작업 ID 추출 및 로깅
                if 'Location' in response.headers:
                    job_uri = response.headers['Location']
                    logger.info(f"BIOS 리셋 작업 ID: {job_uri}")
                return True
            else:
                logger.error(f"BIOS 리셋 실패. 상태 코드: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"BIOS 리셋 중 오류 발생: {str(e)}")
            raise

    def get_bios_settings(self) -> dict:
        """
        현재 BIOS 설정을 조회합니다.

        Returns:
            dict: 현재 BIOS 설정 정보
        """
        try:
            logger.info("BIOS 설정 조회 시도")
            response = self.session.get(self.endpoints.bios_settings)
            
            if response.status_code == 200:
                logger.info("BIOS 설정 조회 성공")
                return response.json().get('Attributes', {})
            else:
                logger.error(f"BIOS 설정 조회 실패. 상태 코드: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"BIOS 설정 조회 중 오류 발생: {str(e)}")
            raise

    def update_firmware(self, file_path: str) -> bool:
        """
        펌웨어 업데이트를 시작합니다.

        Args:
            file_path (str): 펌웨어 파일 경로

        Returns:
            bool: 업데이트 작업이 성공적으로 큐에 추가되었는지 여부
        """
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = self.session.post(
                    self.endpoints.firmware_update,
                    files=files,
                    auth=self.auth,
                    verify=False
                )
                
                if response.status_code in [200, 202]:
                    logger.info("펌웨어 업데이트 작업이 성공적으로 큐에 추가됨")
                    return True
                else:
                    logger.error(f"펌웨어 업데이트 실패. 상태 코드: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"펌웨어 업데이트 중 오류 발생: {str(e)}")
            raise

    def update_firmware_multipart(self, file_path: str) -> bool:
        """
        대용량 펌웨어 파일을 멀티파트 업로드로 업데이트합니다.

        Args:
            file_path (str): 펌웨어 파일 경로

        Returns:
            bool: 업데이트 작업이 성공적으로 큐에 추가되었는지 여부
        """
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = self.session.post(
                    self.endpoints.firmware_multipart_update,
                    files=files,
                    auth=self.auth,
                    verify=False
                )
                
                if response.status_code in [200, 202]:
                    logger.info("멀티파트 펌웨어 업데이트 작업이 성공적으로 큐에 추가됨")
                    return True
                else:
                    logger.error(f"멀티파트 펌웨어 업데이트 실패. 상태 코드: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"멀티파트 펌웨어 업데이트 중 오류 발생: {str(e)}")
            raise

    def get_firmware_rollback_list(self) -> list:
        """
        롤백 가능한 펌웨어 목록을 조회합니다.

        Returns:
            list: 롤백 가능한 펌웨어 목록
        """
        try:
            response = self.session.get(
                self.endpoints.firmware_inventory,
                auth=self.auth,
                verify=False
            )
            
            if response.status_code == 200:
                firmware_list = []
                for member in response.json().get('Members', []):
                    if member.get('RollbackSupported', False):
                        firmware_list.append({
                            'Id': member.get('Id'),
                            'Name': member.get('Name'),
                            'Version': member.get('Version')
                        })
                return firmware_list
            else:
                logger.error(f"펌웨어 목록 조회 실패. 상태 코드: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"펌웨어 목록 조회 중 오류 발생: {str(e)}")
            raise

    def rollback_firmware(self, firmware_id: str) -> bool:
        """
        특정 펌웨어를 이전 버전으로 롤백합니다.

        Args:
            firmware_id (str): 롤백할 펌웨어 ID

        Returns:
            bool: 롤백 작업이 성공적으로 큐에 추가되었는지 여부
        """
        try:
            response = self.session.post(
                self.endpoints.firmware_rollback,
                json={'FirmwareId': firmware_id},
                auth=self.auth,
                verify=False
            )
            
            if response.status_code in [200, 202]:
                logger.info("펌웨어 롤백 작업이 성공적으로 큐에 추가됨")
                return True
            else:
                logger.error(f"펌웨어 롤백 실패. 상태 코드: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"펌웨어 롤백 중 오류 발생: {str(e)}")
            raise

    def get_firmware_settings(self) -> dict:
        """
        펌웨어 업데이트 설정을 조회합니다.

        Returns:
            dict: 현재 펌웨어 설정
        """
        try:
            response = self.session.get(
                self.endpoints.firmware_settings,
                auth=self.auth,
                verify=False
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"펌웨어 설정 조회 실패. 상태 코드: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"펌웨어 설정 조회 중 오류 발생: {str(e)}")
            raise

    def update_firmware_settings(self, settings: dict) -> bool:
        """
        펌웨어 업데이트 설정을 변경합니다.

        Args:
            settings (dict): 변경할 설정

        Returns:
            bool: 설정 변경 성공 여부
        """
        try:
            response = self.session.patch(
                self.endpoints.firmware_settings,
                json=settings,
                auth=self.auth,
                verify=False
            )
            
            if response.status_code in [200, 204]:
                logger.info("펌웨어 설정이 성공적으로 업데이트됨")
                return True
            else:
                logger.error(f"펌웨어 설정 업데이트 실패. 상태 코드: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"펌웨어 설정 업데이트 중 오류 발생: {str(e)}")
            raise

    def get_firmware_queue(self) -> list:
        """
        펌웨어 업데이트 대기열을 조회합니다.

        Returns:
            list: 대기열에 있는 작업 목록
        """
        try:
            response = self.session.get(
                self.endpoints.firmware_queue,
                auth=self.auth,
                verify=False
            )
            
            if response.status_code == 200:
                return response.json().get('Members', [])
            else:
                logger.error(f"펌웨어 대기열 조회 실패. 상태 코드: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"펌웨어 대기열 조회 중 오류 발생: {str(e)}")
            raise

    def cancel_firmware_update(self, job_id: str) -> bool:
        """
        진행 중인 펌웨어 업데이트를 취소합니다.

        Args:
            job_id (str): 취소할 작업 ID

        Returns:
            bool: 취소 성공 여부
        """
        try:
            response = self.session.delete(
                f"{self.endpoints.firmware_queue}/{job_id}",
                auth=self.auth,
                verify=False
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"펌웨어 업데이트 작업 {job_id}가 성공적으로 취소됨")
                return True
            else:
                logger.error(f"펌웨어 업데이트 작업 취소 실패. 상태 코드: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"펌웨어 업데이트 작업 취소 중 오류 발생: {str(e)}")
            raise

    def restart_system(self):
        """시스템을 즉시 재시작합니다."""
        try:
            # Redfish API를 사용하여 시스템 재시작
            endpoint = f"{self.endpoints.base_url}/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
            payload = {"ResetType": "GracefulRestart"}
            
            response = self.session.post(
                endpoint,
                json=payload,
                auth=self.auth,
                verify=False,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("시스템 재시작 요청 성공")
            return True
        except Exception as e:
            logger.error(f"시스템 재시작 실패: {str(e)}")
            raise

    def schedule_system_restart(self, restart_time):
        """시스템 재시작을 예약합니다."""
        try:
            # iDRAC Job Service를 사용하여 재시작 작업 예약
            endpoint = f"{self.endpoints.base_url}/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"
            payload = {
                "JobName": "SystemRestart",
                "ScheduledStartTime": restart_time.toString(Qt.ISODate),
                "Command": "GracefulRestart"
            }
            
            response = self.session.post(
                endpoint,
                json=payload,
                auth=self.auth,
                verify=False,
                timeout=self.timeout
            )
            response.raise_for_status()
            job_id = response.json().get('Id')
            logger.info(f"시스템 재시작 예약 성공 (Job ID: {job_id})")
            return job_id
        except Exception as e:
            logger.error(f"시스템 재시작 예약 실패: {str(e)}")
            raise
