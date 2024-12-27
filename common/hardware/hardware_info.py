import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from config import data_config, dell_config
from common.data.data_processor import DataProcessor
from dell_logging.log_config import logger, setup_logging
from error.error_handler import ErrorHandler
from utils.utils import retry_with_backoff, get_nested_value, convert_capacity, performance_logger
from common.cache.cache_manager import CacheManager
from utils.async_utils import run_with_timeout
from config import *

setup_logging()

class HardwareInfoService:
    def __init__(self, endpoint_manager, main_app, session):
        self.endpoint_manager = endpoint_manager
        self.main_app = main_app
        self.session = session
        self._connection_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(3)
        self.data_processor = DataProcessor()
        self.data_processor.set_hardware_service(self)
        self.cache = {}

    async def initialize(self):
        try:
            # 세션 검증
            if not self.session:
                raise ValueError("Session is not initialized")
            
            # 기본 URL 설정 확인
            if not dell_config.DellConfig.BASE_URL:
                server = self.main_app.server_config.get_server()
                if server:
                    dell_config.DellConfig.update_config(server)
                else:
                    raise ValueError("Server configuration not found")
            
            # 연결 테스트
            if not await self.check_connection():
                raise ConnectionError("Failed to establish connection")
                
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise

    async def check_connection(self):
        try:
            async with self._connection_lock:
                url = self.get_full_url("/redfish/v1/Systems")  # get_full_url 메서드 사용
                async with self.session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False

    async def close(self):
        self.cache.clear()

    def get_full_url(self, endpoint):
        base_url = dell_config.DellConfig.get_url('BASE_URL').rstrip('/')  # dell_config.DellConfig의 메서드 사용
        endpoint = endpoint.lstrip('/')
        return f"{base_url}/{endpoint}"

    @retry_with_backoff(max_retries=3, base_delay=1, max_delay=10)
    async def fetch_hardware_info(self, url: str, data_type: str):
        """하드웨어 정보를 가져옵니다."""
        try:
            if not self.session or self.session.closed:
                logger.warning(f"{data_type} 조회 중 세션이 없거나 닫힘")
                await self.initialize()
            
            # URL이 이미 https://로 시작하는 경우 그대로 사용
            if not url.startswith('https://'):
                url = f"{dell_config.DellConfig.get_url('BASE_URL').rstrip('/')}/{url.lstrip('/')}"
            
            logger.debug(f"{data_type} 데이터 요청 URL: {url}")
            
            try:
                async with self.session.get(url, ssl=False, timeout=30) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            logger.debug(f"{data_type} 데이터 조회 성공")
                            return data
                        except Exception as e:
                            logger.error(f"{data_type} JSON 파싱 오류: {str(e)}")
                            text_response = await response.text()
                            logger.debug(f"{data_type} 원본 응답: {text_response[:200]}")
                            return None
                    else:
                        logger.error(f"{data_type} 데이터 조회 실패. 상태 코드: {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.error(f"{data_type} 요청 시간 초과")
                return None
            except aiohttp.ClientError as e:
                logger.error(f"{data_type} 클라이언트 오류: {str(e)}")
                return None
                    
        except Exception as e:
            logger.error(f"{data_type} 데이터 조회 중 오류: {str(e)}")
            return None

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def fetch_members(self, base_url: str, data_type: str):
        async with self.semaphore:
            url = self.get_full_url(base_url)
            data = await self.fetch_hardware_info(url, data_type)
        if not data or 'Members' not in data:
            raise ValueError(f'Failed to fetch {data_type} or no members found')
        
        results = []
        for member in data['Members']:
            member_url = self.get_full_url(member['@odata.id'])
            result = await self.fetch_hardware_info(member_url, f'{data_type} detail')
            if result:
                results.append(result)
        return results

    async def get_system_info(self):
        """시스템의 상세 정보를 가져옵니다."""
        try:
            logger.info("시스템 정보 수집 시작")
            system_url = f"{self.get_full_url('')}/redfish/v1/Systems/System.Embedded.1"
            logger.debug(f"시스템 정보 URL: {system_url}")
            
            system_data = await self.fetch_hardware_info(system_url, "system_info")
            if not system_data:
                logger.error("시스템 데이터를 가져올 수 없습니다")
                return None
                
            # 필요한 정보 추출
            system_info = {
                "Model": system_data.get("Model", "Unknown"),
                "Manufacturer": system_data.get("Manufacturer", "Unknown"),
                "SerialNumber": system_data.get("SerialNumber", "Unknown"),
                "PartNumber": system_data.get("PartNumber", "Unknown"),
                "SystemType": system_data.get("SystemType", "Unknown"),
                "HostName": system_data.get("HostName", "Unknown"),
                "Status": system_data.get("Status", {}),
                "BiosVersion": system_data.get("BiosVersion", "Unknown"),
                "ProcessorSummary": system_data.get("ProcessorSummary", {}),
                "MemorySummary": system_data.get("MemorySummary", {})
            }
            
            logger.info("시스템 정보 수집 완료")
            return system_info
            
        except Exception as e:
            logger.error(f"시스템 정보 수집 중 오류 발생: {e}")
            raise

    async def get_part_status(self):
        """파트 상태 정보를 가져옵니다."""
        try:
            start_time = time.time()
            
            processors = await self.fetch_members(dell_config.DellConfig.ENDPOINTS.PROCESSORS, "프로세서")
            memory = await self.fetch_members(dell_config.DellConfig.ENDPOINTS.MEMORY, "메모리")
            storage = await self.fetch_members(dell_config.DellConfig.ENDPOINTS.STORAGE, "스토리지")
            
            cpu_status = await self.data_processor.process_processors(processors)
            memory_result = self.data_processor.process_memory(memory)
            memory_status, cpu1_empty_slots, cpu2_empty_slots = memory_result
            raid_status = await self.data_processor.process_storage(storage)
            
            end_time = time.time()
            logger.info(f"get_part_status 실행 시간: {end_time - start_time:.2f}초")
            
            return cpu_status, memory_status, cpu1_empty_slots, cpu2_empty_slots, raid_status
        except Exception as e:
            logger.error(f"파트 상태 조회 중 오류 발생: {str(e)}")
            return None, None, 0, 0, "RAID 정보 없음"

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def get_manufacturer_info(self):
        """제조사 정보를 가져옵니다."""
        try:
            # CPU 정보 가져오기
            processor_data = await self.fetch_members(dell_config.DellConfig.ENDPOINTS.PROCESSORS, "프로세서")
            cpu_info = self.data_processor.process_manufacturer_cpu(processor_data)

            # 메모리 정보 가져오기
            memory_data = await self.fetch_members(dell_config.DellConfig.ENDPOINTS.MEMORY, "메모리")
            memory_info = self.data_processor.process_manufacturer_memory(memory_data)

            # 스토리지 정보 가져오기
            storage_data = await self.fetch_members(dell_config.DellConfig.ENDPOINTS.STORAGE, "스토리지")
            storage_info = await self.data_processor.process_manufacturer_storage(storage_data)

            # CPU, 메모리, 스토리지 정보를 조합
            combined_info = []
            if cpu_info:
                combined_info.append(cpu_info)
            if memory_info:
                combined_info.append(memory_info)
            if storage_info:
                combined_info.append(storage_info)

            return "\n".join(combined_info)

        except Exception as e:
            logger.error(f"제조사 정보 조회 중 오류: {str(e)}")
            return None

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def get_bios_info(self):
        """BIOS 설정 정보를 가져옵니다."""
        async with self.semaphore:
            try:
                bios_settings = "BIOS 정보를 가져올 수 없습니다"
                
                try:
                    bios_url = self.get_full_url(dell_config.DellConfig.ENDPOINTS.BIOS)
                    bios_data = await self.fetch_hardware_info(bios_url, "BIOS")
                    if bios_data:
                        bios_settings = self.data_processor.process_bios_settings(bios_data.get('Attributes', {}))
                except Exception as e:
                    logger.error(f"BIOS 설정 정보 조회 중 오류: {e}")
                
                return bios_settings
                
            except Exception as e:
                logger.error(f"BIOS 설정 정보 조회 중 오류 발생: {e}")
                return "BIOS 설정 정보 조회 중 오류 발생"

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def get_nic_settings(self) -> List[str]:
        """NIC 설정 정보를 가져옵니다."""
        async with self.semaphore:
            try:
                nic_info = ["NIC 설정 정보", "=" * 40]
                
                # NIC 어댑터 정보 조회
                adapters = await self.fetch_members(dell_config.DellConfig.ENDPOINTS.NETWORK_ADAPTERS, "NetworkAdapters")
                if not adapters:
                    return ["NIC 정보를 가져올 수 없습니다"]

                for adapter in adapters:
                    if not adapter.get('NetworkDeviceFunctions', {}).get('@odata.id'):
                        continue
                        
                    # NIC 기능 정보 조회
                    functions = await self.fetch_members(adapter['NetworkDeviceFunctions']['@odata.id'], "NetworkDeviceFunctions")
                    for func in functions:
                        if 'Id' not in func:
                            continue
                        
                        # Id 출력
                        nic_info.extend([f"\nId: {func['Id']}", "=" * 40])
                        
                        # DellNetworkAttributes 조회
                        try:
                            attrs_url = f"/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/{adapter['Id']}/NetworkDeviceFunctions/{func['Id']}/Oem/Dell/DellNetworkAttributes/{func['Id']}"
                            attrs = await self.fetch_hardware_info(self.get_full_url(attrs_url), "DellNetworkAttributes")
                            
                            if attrs and 'Attributes' in attrs:
                                for key, value in attrs['Attributes'].items():
                                    nic_info.append(f"- {key}: {value}")
                        except Exception as e:
                            logger.error(f"DellNetworkAttributes 조회 실패: {str(e)}")
            
                return nic_info
                
            except Exception as e:
                logger.error(f"NIC 설정 정보 조회 중 오류: {str(e)}")
                return ["NIC 설정 정보 조회 중 오류 발생"]

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def get_firmware_info(self):
        """펌웨어 정보를 가져옵니다."""
        async with self.semaphore:
            try:
                # 세션이 없거나 닫혔으면 재연결
                if not self.session or self.session.closed:
                    logger.info("세션이 닫혔거나 없음. 재연결 시도...")
                    await self.initialize()
                    
                # URL 끝에 슬래시(/) 추가
                firmware_url = f"{self.get_full_url(dell_config.DellConfig.ENDPOINTS.FIRMWARE_INVENTORY)}/"
                logger.info(f"Fetching firmware inventory from URL: {firmware_url}")
                
                # 첫 번째 시도
                firmware_data = await self.fetch_hardware_info(firmware_url, "펌웨어 인벤토리")
                
                # 응답이 없거나 Members가 없으면
                if not firmware_data or 'Members' not in firmware_data:
                    logger.warning("펌웨어 인벤토리를 가져올 수 없습니다. 세션 재연결 후 재시도...")
                    # 세션 재연결
                    await self.initialize()
                    # 두 번째 시도
                    firmware_data = await self.fetch_hardware_info(firmware_url, "펌웨어 인벤토리")
                    
                if not firmware_data or 'Members' not in firmware_data:
                    logger.error("재시도 후에도 펌웨어 인벤토리를 가져올 수 없습니다.")
                    return "펌웨어 정보를 가져올 수 없습니다."
                
                firmware_details = []
                for member in firmware_data['Members']:
                    if '@odata.id' in member:
                        firmware_url = self.get_full_url(member['@odata.id'])
                        detail = await self.fetch_hardware_info(firmware_url, "펌웨어 상세")
                        if detail:
                            firmware_details.append(detail)
                
                return self.data_processor.process_firmware_details(firmware_details)
                
            except Exception as e:
                logger.error(f"펌웨어 정보 조회 중 오류: {str(e)}")
                return "펌웨어 정보 조회 중 오류가 발생했습니다."

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def get_system_logs(self):
        async with self.semaphore:
            logs_url = self.get_full_url(dell_config.DellConfig.ENDPOINTS.LOG_ENTRIES)
            logs_data = await self.fetch_hardware_info(logs_url, "시스템 로그")
            
            all_logs = []
            
            # 페이징 처리: @odata.nextLink가 존재하면 계속해서 다음 페이지의 로그를 가져옴
            while logs_data and 'Members' in logs_data:
                all_logs.extend(logs_data['Members'])
                
                # 다음 페이지가 있는지 확인
                next_link = logs_data.get('@odata.nextLink')
                if next_link:
                    logs_data = await self.fetch_hardware_info(next_link, "시스템 로그 (다음 페이지)")
                else:
                    break
            
            if all_logs:
                return self.data_processor.process_system_logs(all_logs)
            else:
                raise ValueError("로그 데이터가 없거나 형식이 잘못되었습니다.")

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def update_bios_settings(self, new_settings: Dict[str, Any]):
        async with self.semaphore:
            try:
                # BIOS 설정 업데이트
                url = f"{dell_config.DellConfig.URLS.BASE_URL}{dell_config.DellConfig.ENDPOINTS.BIOS}/Settings"
                payload = {"Attributes": new_settings}
                async with self.session.patch(url, json=payload) as response:
                    response.raise_for_status()
                    if response.status != 200:
                        raise ValueError(f"BIOS 업데이트 실패: HTTP {response.status}")

                # Job queue 생성
                job_id = await self.create_bios_config_job()

                return job_id
            except Exception as e:
                logger.error(f"BIOS 설정 업데이트 중 오류 발생: {e}")
                raise

    async def create_bios_config_job(self):
        url = f"{dell_config.DellConfig.URLS.BASE_URL}/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"
        payload = {
            "TargetSettingsURI": f"{dell_config.DellConfig.URLS.BASE_SYSTEM_URL}/Bios/Settings"
        }
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            if response.status == 200:
                job_data = await response.json()
                return job_data.get('Id')
            else:
                raise ValueError(f"BIOS 설정 job 생성 실패: HTTP {response.status}")

    async def reboot_server(self):
        url = f"{dell_config.DellConfig.URLS.BASE_SYSTEM_URL}/Actions/ComputerSystem.Reset"
        payload = {"ResetType": "GracefulRestart"}
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            if response.status != 204:
                raise ValueError(f"서버 재부팅 요청 실패: HTTP {response.status}")

    @retry_with_backoff(max_retries=3, base_delay=2, max_delay=30)
    @ErrorHandler.handle_error
    async def collect_tsr_log(self):
        async with self.semaphore:
            try:
                url = f"{dell_config.DellConfig.URLS.BASE_URL}/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistCollection"
                payload = {
                    "ShareType": "Local",
                    "DataSelectorArrayIn": ["OSAppAll", "TTYLog"]
                }
                async with self.session.post(url, json=payload) as response:
                    if response.status == 202:
                        return "TSR 로그 수집이 시작되었습니다. 잠시 후 다시 확인해주세요."
                    else:
                        raise ValueError(f"TSR 로그 수집 실패: HTTP {response.status}")
            except Exception as e:
                logger.error(f"TSR 로그 수집 중 오류 발생: {e}")
                raise

    async def get_smart_logs(self):
        """각 드라이브의 SMART 로그 정보를 가져옵니다."""
        try:
            logger.info("SMART 로그 수집 시작")
            # 먼저 스토리지 정보를 가져옵니다
            storage_url = f"{self.get_full_url('')}/redfish/v1/Systems/System.Embedded.1/Storage"
            logger.debug(f"스토리지 정보 URL: {storage_url}")
            storage_data = await self.fetch_hardware_info(storage_url, "storage")
            logger.debug(f"스토리지 데이터: {storage_data}")
            
            if not storage_data:
                logger.error("스토리지 데이터를 가져올 수 없습니다")
                return None
            
            smart_logs = []
            # 각 드라이브에 대해 SMART 로그를 가져옵니다
            drives = storage_data.get("Drives", [])
            logger.info(f"발견된 드라이브 수: {len(drives)}")
            
            for drive in drives:
                drive_id = drive.get("Id")
                if drive_id:
                    logger.debug(f"드라이브 {drive_id} SMART 로그 수집 시작")
                    smart_log_url = self.get_full_url(
                        Endpoints.SMART_LOG.format(drive_id=drive_id)
                    )
                    logger.debug(f"SMART 로그 URL: {smart_log_url}")
                    try:
                        smart_log = await self.fetch_hardware_info(smart_log_url, "smart_log")
                        logger.debug(f"드라이브 {drive_id} SMART 로그: {smart_log}")
                        if smart_log:
                            smart_log["DriveInfo"] = {
                                "Name": drive.get("Name", "Unknown"),
                                "Model": drive.get("Model", "Unknown"),
                                "SerialNumber": drive.get("SerialNumber", "Unknown"),
                            }
                            smart_logs.append(smart_log)
                            logger.info(f"드라이브 {drive_id} SMART 로그 수집 성공")
                    except Exception as e:
                        logger.warning(f"드라이브 {drive_id}의 SMART 로그를 가져오는데 실패했습니다: {e}")
            
            processed_logs = self.data_processor.process_smart_logs(smart_logs)
            logger.info(f"SMART 로그 처리 완료. 수집된 로그 수: {len(processed_logs)}")
            return processed_logs
        except Exception as e:
            logger.error(f"SMART 로그 수집 중 오류 발생: {e}")
            raise