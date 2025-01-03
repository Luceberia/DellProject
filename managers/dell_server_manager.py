from config.system.log_config import setup_logging
import requests
from endpoints.redfish_endpoints import RedfishEndpoints
import urllib3
import time
import os
from pathlib import Path

# logger 객체 생성
logger = setup_logging()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DellServerManager:
    def __init__(self, ip: str, port: str, auth: tuple):
        self.endpoints = RedfishEndpoints(ip, port)
        self.auth = auth
        self.timeout = 5  # 기본 타임아웃 5초
        self.session = requests.Session()
        self.session.verify = False  # SSL 커뮤리를 불행
        
    def fetch_basic_info(self):
        """시스템 기본 정보 조회"""
        try:
            responses = {
                'system': self.session.get(self.endpoints.system, auth=self.auth, verify=False),
                'bios': self.session.get(self.endpoints.bios, auth=self.auth, verify=False),
                'idrac': self.session.get(self.endpoints.managers, auth=self.auth, verify=False)
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
        except Exception as e:
            logger.error(f"기본 정보 조회 실패: {e}")
            raise

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
        return self.fetch_detailed_info(self.endpoints.power)

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
                logger.debug(f"프로세서 정보 조회 중 오류 발생: {str(e)}")
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
                    logger.debug("PCIe 장치 정보를 지원하지 않는 시스템입니다.")
                else:
                    logger.error(f"PCIe 장치 정보 조회 중 오류 발생: {str(e)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"PCIe 장치 정보 조회 중 오류 발생: {str(e)}")
            
            return {'GPUDevices': result}
            
        except Exception as e:
            logger.debug(f"GPU 정보 조회 중 오류 발생: {str(e)}")
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
            response = self.session.post(self.endpoints.clear_sel_log, auth=self.auth, verify=False)
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
        """전체 펌웨어 인벤토리 정보 조회"""
        try:
            response = requests.get(
                self.endpoints.firmware_inventory,
                auth=self.auth,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"펌웨어 인벤토리 조회 실패: {str(e)}")
            raise

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

    def collect_tsr_log(self, progress_callback=None):
        try:
            basic_info = self.fetch_basic_info()
            service_tag = basic_info['system'].get('ServiceTag', "Unknown")

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"TSR_Log_{service_tag}_{timestamp}.zip"
            
            data = {
                "ShareType": "Local",
                "DataSelectorArrayIn": ["SelLog", "TTYLog"],
                "FileName": filename
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

    def clear_job_queue(self):
        """전체 Job 큐 삭제"""
        try:
            url = f"{self.endpoints.job_collection}/Actions/JobService.DeleteJobQueue"
            payload = {"JobID": "JID_CLEARALL"}
            response = self.session.post(url, json=payload, auth=self.auth, verify=False)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Job 큐 삭제 실패: {str(e)}")
            raise