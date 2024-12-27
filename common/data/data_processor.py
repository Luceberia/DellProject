import asyncio
import aiohttp
from typing import Dict, List, Any
from dell_logging.log_config import logger
from error.error_handler import ErrorHandler
from config import data_config, dell_config
from utils.utils import retry_with_backoff, get_nested_value, convert_capacity, performance_logger


class DataProcessor:
    def __init__(self):
        self.common_fields = data_config.CommonFields()
        self.hardware_service = None

    async def process_processors(self, processors):
        if not processors or isinstance(processors, Exception):
            return "CPU 정보 없음"
        
        formatted_info = []
        try:
            # 헤더와 구분선 추가
            formatted_info.extend([
                "CPU Information:",
                "=" * 40,
                ""
            ])

            for proc in processors:
                if isinstance(proc, dict):
                    socket_id = proc.get('Id', '')
                    
                    # 각 CPU 정보를 별도의 문자열로 구성
                    cpu_info = [
                        f"CPU 이름: {socket_id}",
                        f"모델: {proc.get('Model', '정보없음')}",
                        f"코어: {proc.get('TotalCores', '정보없음')}",
                        f"스레드: {proc.get('TotalThreads', '정보없음')}",
                        f"상태: {proc.get('Status', {}).get('Health', '정보없음')}",
                        "-" * 20,  # 구분선 추가
                        ""
                    ]
                    
                    formatted_info.extend(cpu_info)
            
            # 최종 결과 조합
            return "\n".join(formatted_info) if formatted_info else "CPU 정보 없음"
            
        except Exception as e:
            logger.error(f"프로세서 정보 처리 중 오류: {e}")
            return "CPU 정보 처리 중 오류"

    def process_memory(self, memory):
        if not memory or isinstance(memory, Exception):
            return [], 0, 0
        
        memory_status = []
        cpu1_empty_slots = cpu2_empty_slots = 0
        
        try:
            # 헤더와 구분선 추가
            memory_status.extend([
                "Memory Information:", 
                "=" * 40,
                ""
            ])

            # DIMM 슬롯별로 정렬
            sorted_memory = sorted(memory, key=lambda x: x.get('Name', ''))
            current_socket = None
            
            for mem in sorted_memory:
                if not isinstance(mem, dict):
                    continue
                
                slot_name = mem.get('Name', '')
                if mem.get('Status', {}).get('Health', 'Absent') == 'Absent':
                    if 'DIMM.Socket.A' in slot_name:
                        cpu1_empty_slots += 1
                    elif 'DIMM.Socket.B' in slot_name:
                        cpu2_empty_slots += 1
                    continue
                
                # 소켓이 바뀌면 빈 줄 추가
                current = slot_name.split('.')[2] if len(slot_name.split('.')) > 2 else ''
                if current_socket and current_socket != current:
                    memory_status.append("")
                current_socket = current
                
                dimm_id = slot_name.split('.')[-1] if slot_name else '정보없음'
                capacity = convert_capacity(mem.get('CapacityMiB', 0))
                status = mem.get('Status', {}).get('Health', '정보없음')
                
                # 각 메모리 정보를 별도의 줄로 구성
                memory_info = [
                    f"메모리 이름: DIMM {dimm_id}",
                    f"용량: {capacity}",
                    f"상태: {status}",
                    "-" * 20,  # 구분선 추가
                    ""
                ]
                
                memory_status.extend(memory_info)
            
            # CPU처럼 하나의 문자열로 합쳐서 리스트로 반환
            return "\n".join(memory_status), cpu1_empty_slots, cpu2_empty_slots
            
        except Exception as e:
            logger.error(f"메모리 정보 처리 중 오류: {e}")
            return [], 0, 0

    def set_hardware_service(self, hardware_service):
        """HardwareInfoService 인스턴스 설정"""
        if not self.hardware_service:
            self.hardware_service = hardware_service

    def format_volume_info(self, volume_info):
        """볼륨 정보를 포맷팅합니다."""
        try:
            if not volume_info:
                logger.warning("볼륨 정보가 없습니다.")
                return None

            # 기본 볼륨 정보 구성
            result = {
                'DeviceName': volume_info.get('DisplayName') or volume_info.get('Name', '정보없음'),
                'RAIDType': volume_info.get('RAIDType', '정보없음'),
                'Capacity': convert_capacity(volume_info.get('CapacityBytes', 0), is_bytes=True),
                'Status': volume_info.get('Status', {}).get('Health', '정보없음')
            }
            
            # Dell 특화 정보 추가
            if 'Oem' in volume_info and 'Dell' in volume_info['Oem']:
                dell_info = volume_info['Oem']['Dell'].get('DellVolume', {})
                if dell_info:
                    result['Status'] = dell_info.get('RaidStatus', result['Status'])
            
            return result
        except Exception as e:
            logger.error(f"볼륨 정보 포맷팅 중 오류: {str(e)}")
            return None

    async def process_storage(self, storage):
        """스토리지 정보를 처리합니다."""
        if not storage or isinstance(storage, Exception):
            logger.info("스토리지 정보를 찾을 수 없습니다.")
            return "RAID 정보 없음"
        
        raid_status = []
        semaphore = asyncio.Semaphore(3)  # 최대 3개의 동시 요청으로 제한
        
        try:
            # 볼륨 정보 조회를 위한 내부 함수
            async def fetch_volume_info(volume, url):
                async with semaphore:
                    try:
                        volume_info = await self.hardware_service.fetch_hardware_info(url, "Volume Info")
                        if volume_info:
                            return self.format_volume_info(volume_info)
                        logger.warning(f"볼륨 정보를 찾을 수 없습니다: {url}")
                        return None
                    except Exception as e:
                        logger.error(f"Volume 정보 조회 중 오류: {str(e)}")
                        return None

            # 스토리지 컨트롤러 정보 처리
            raid_status.append("Volume Information:")
            raid_status.append("=" * 40)  # 구분선 추가
            raid_status.append("")  # 헤더 후 줄바꿈
            
            for controller in storage:
                controller_id = controller.get('Id', '알 수 없음')
                raid_status.extend([
                    f"컨트롤러: {controller_id}",
                    "-" * 30,  # 구분선 추가
                    ""
                ])
                
                # 디스크 베이 정보 조회
                if 'Drives' in controller and '@odata.id' in controller['Drives']:
                    drives_url = controller['Drives']['@odata.id']
                    drives_data = await self.hardware_service.fetch_hardware_info(drives_url, "Physical Drives")
                    
                    if drives_data and 'Members' in drives_data:
                        raid_status.append("물리 디스크:")
                        raid_status.append("-" * 20)  # 구분선 추가
                        raid_status.append("")
                        
                        for drive in drives_data['Members']:
                            drive_info = await self.hardware_service.fetch_hardware_info(drive['@odata.id'], "Drive Info")
                            if drive_info:
                                raid_status.extend([
                                    f"디스크 베이: {drive_info.get('Name', '정보없음')}",
                                    f"모델: {drive_info.get('Model', '정보없음')}",
                                    f"용량: {convert_capacity(drive_info.get('CapacityBytes', 0), is_bytes=True)}",
                                    f"상태: {drive_info.get('Status', {}).get('Health', '정보없음')}",
                                    f"디스크 타입: {drive_info.get('MediaType', '정보없음')}",
                                    f"프로토콜: {drive_info.get('Protocol', '정보없음')}",
                                    f"제조사: {drive_info.get('Manufacturer', '정보없음')}",
                                    "-" * 15,  # 구분선 추가
                                    ""
                                ])
                
                # RAID 볼륨 정보 조회
                if 'Volumes' in controller and '@odata.id' in controller['Volumes']:
                    volumes_url = controller['Volumes']['@odata.id']
                    try:
                        volumes_data = await self.hardware_service.fetch_hardware_info(volumes_url, "Virtual Disks")
                        if volumes_data and 'Members' in volumes_data and volumes_data['Members']:
                            raid_status.append("가상 디스크:")
                            raid_status.append("-" * 20)  # 구분선 추가
                            raid_status.append("")
                            
                            volume_tasks = []
                            for volume in volumes_data['Members']:
                                if '@odata.id' in volume:
                                    volume_tasks.append(fetch_volume_info(volume, volume['@odata.id']))
                            
                            volume_results = await asyncio.gather(*volume_tasks)
                            has_valid_volume = False
                            
                            for result in volume_results:
                                if isinstance(result, dict):
                                    has_valid_volume = True
                                    raid_status.extend([
                                        f"디바이스 이름: {result['DeviceName']}",
                                        f"RAID 레벨: {result['RAIDType']}",
                                        f"용량: {result['Capacity']}",
                                        f"상태: {result['Status']}",
                                        "-" * 15,  # 구분선 추가
                                        ""
                                    ])
                            
                            if not has_valid_volume:
                                raid_status.extend(["가상 디스크를 찾을 수 없습니다.", ""])
                        else:
                            logger.info(f"컨트롤러 {controller_id}에 가상 디스크가 구성되어 있지 않습니다.")
                    except Exception as e:
                        logger.error(f"컨트롤러 {controller_id}의 볼륨 정보 조회 중 오류: {e}")
                        raid_status.extend(["가상 디스크 정보를 가져오는 중 오류가 발생했습니다.", ""])

            return "\n".join(filter(None, raid_status)) if len(raid_status) > 1 else "RAID 정보 없음"
        
        except Exception as e:
            logger.error(f"스토리지 정보 처리 중 오류: {str(e)}")
            return f"스토리지 정보 처리 중 오류: {str(e)}"

    def process_manufacturer_cpu(self, processor_data):
        """CPU 제조사 정보를 처리합니다."""
        if not processor_data or isinstance(processor_data, Exception):
            return "CPU 정보 없음"
            
        cpu_info = []
        try:
            # 헤더 추가
            cpu_info.extend([
                "CPU 제조사 정보:",
                "=" * 40,
                ""
            ])

            for proc in processor_data:
                if not isinstance(proc, dict):
                    continue
                    
                socket_id = proc.get('Id', '')
                manufacturer = proc.get('Manufacturer', '정보없음')
                model = proc.get('Model', '정보없음')
                
                cpu_info.extend([
                    f"CPU 이름: {socket_id}",
                    f"제조사: {manufacturer}",
                    f"모델: {model}",
                    "-" * 20,
                    ""
                ])
            
            return "\n".join(cpu_info) if cpu_info else "CPU 정보 없음"
            
        except Exception as e:
            logger.error(f"CPU 제조사 정보 처리 중 오류: {e}")
            return "CPU 정보 처리 중 오류"

    def process_manufacturer_memory(self, memory_data):
        if not memory_data or isinstance(memory_data, Exception):
            return "메모리 정보 없음"
            
        memory_info = []
        try:
            # 헤더 추가
            memory_info.extend([
                "메모리 제조사 정보:",
                "=" * 40,
                ""
            ])

            # DIMM 슬롯별로 정렬
            sorted_memory = sorted(memory_data, key=lambda x: x.get('Name', ''))
            
            for mem in sorted_memory:
                if not isinstance(mem, dict):
                    continue
                    
                slot_name = mem.get('Name', '')
                manufacturer = mem.get('Manufacturer', '정보없음')
                model = mem.get('PartNumber', '정보없음').strip()
                status = mem.get('Status', {}).get('Health', '정보없음')
                capacity = convert_capacity(mem.get('CapacityMiB', 0))
                
                # 각 메모리 정보를 구성
                memory_info.extend([
                    f"슬롯: {slot_name}",
                    f"제조사: {manufacturer}",
                    f"모델: {model}",
                    f"상태: {status}",
                    f"용량: {capacity}",
                    "-" * 20,
                    ""
                ])
            
            return "\n".join(memory_info) if memory_info else "메모리 정보 없음"
            
        except Exception as e:
            logger.error(f"메모리 제조사 정보 처리 중 오류: {e}")
            return "메모리 정보 처리 중 오류"

    async def process_manufacturer_storage(self, storage_data):
        if not storage_data or isinstance(storage_data, Exception):
            return "스토리지 정보 없음"
            
        storage_info = []
        try:
            # 헤더 추가
            storage_info.extend([
                "\n스토리지 제조사 정보:",
                "=" * 40,
                ""
            ])
            
            # 컨트롤러별 드라이브 정보를 저장할 딕셔너리
            controller_drives = {}
            
            for controller in storage_data:
                if not isinstance(controller, dict):
                    continue
                
                controller_id = controller.get('@odata.id', '')
                if not controller_id:
                    continue
                
                # 컨트롤러 상세 정보 가져오기
                controller_url = f"{controller_id}/Controllers/{controller.get('Id', '')}"
                controller_data = await self.hardware_service.fetch_hardware_info(controller_url, "컨트롤러")
                
                if controller_data:
                    controller_drives[controller_id] = {
                        'name': controller_data.get('Name', '정보없음'),
                        'manufacturer': controller_data.get('Manufacturer', '정보없음'),
                        'model': controller_data.get('Model', '정보없음'),
                        'firmware': controller_data.get('FirmwareVersion', '정보없음'),
                        'description': controller_data.get('Description', '정보없음'),
                        'drives': {}
                    }
                else:
                    controller_drives[controller_id] = {
                        'name': controller.get('Name', '정보없음'),
                        'manufacturer': controller.get('Manufacturer', '정보없음'),
                        'model': controller.get('Model', '정보없음'),
                        'firmware': '정보없음',
                        'description': controller.get('Description', '정보없음'),
                        'drives': {}
                    }
                
                # 1. 컨트롤러에서 직접 드라이브 참조 확인
                drives = controller.get('Drives', [])
                for drive in drives:
                    if '@odata.id' in drive:
                        drive_url = drive['@odata.id']
                        drive_data = await self.hardware_service.fetch_hardware_info(drive_url, "드라이브")
                        if drive_data:
                            drive_id = drive_data.get('Id', '')
                            if drive_id:
                                controller_drives[controller_id]['drives'][drive_id] = drive_data
                
                # 2. 컨트롤러의 볼륨 확인
                if '@odata.id' in controller:
                    volumes_url = f"{controller['@odata.id']}/Volumes"
                    volumes_data = await self.hardware_service.fetch_hardware_info(volumes_url, "볼륨")
                    
                    if volumes_data and 'Members' in volumes_data:
                        for volume in volumes_data['Members']:
                            if '@odata.id' in volume:
                                volume_url = volume['@odata.id']
                                volume_data = await self.hardware_service.fetch_hardware_info(volume_url, "볼륨 상세")
                                
                                if volume_data and 'Links' in volume_data and 'Drives' in volume_data['Links']:
                                    for drive in volume_data['Links']['Drives']:
                                        if '@odata.id' in drive:
                                            drive_url = drive['@odata.id']
                                            drive_data = await self.hardware_service.fetch_hardware_info(drive_url, "드라이브")
                                            if drive_data:
                                                drive_id = drive_data.get('Id', '')
                                                if drive_id:
                                                    controller_drives[controller_id]['drives'][drive_id] = drive_data
            
            # 컨트롤러별로 정보 출력
            for controller_id, controller_info in controller_drives.items():
                # 컨트롤러 정보 출력
                storage_info.extend([
                    f"컨트롤러: {controller_info['name']}",
                    f"제조사: {controller_info['manufacturer']}",
                    f"모델: {controller_info['model']}",
                    f"펌웨어: {controller_info['firmware']}",
                    f"설명: {controller_info['description']}",
                    "-" * 20,
                    ""
                ])
                
                # 해당 컨트롤러의 드라이브 정보 출력
                sorted_drives = dict(sorted(controller_info['drives'].items()))
                for drive_id, drive in sorted_drives.items():
                    name = drive.get('Name', '정보없음')
                    manufacturer = drive.get('Manufacturer', '정보없음')
                    model = drive.get('Model', '정보없음')
                    capacity = convert_capacity(drive.get('CapacityBytes', 0), is_bytes=True)
                    media_type = drive.get('MediaType', '정보없음')
                    protocol = drive.get('Protocol', '')
                    
                    # 드라이브 타입 결정
                    drive_type = media_type
                    if protocol and protocol.upper() == 'NVME':
                        drive_type = 'NVMe'
                    
                    # RAID 정보 확인
                    raid_info = "정보없음"
                    if 'Links' in drive and 'Volumes' in drive['Links']:
                        volumes = drive['Links']['Volumes']
                        if volumes and len(volumes) > 0:
                            volume_url = volumes[0].get('@odata.id', '')
                            if volume_url:
                                volume_data = await self.hardware_service.fetch_hardware_info(volume_url, "볼륨")
                                if volume_data:
                                    raid_info = volume_data.get('RAIDType', '정보없음')
                    
                    storage_info.extend([
                        f"{name}:",
                        f"  제조사: {manufacturer}",
                        f"  모델: {model}",
                        f"  타입: {drive_type}",
                        f"  용량: {capacity}",
                        f"  RAID: {raid_info}",
                        "-" * 20,
                        ""
                    ])
                
                # 컨트롤러 구분선 추가
                storage_info.extend([
                    "=" * 40,
                    ""
                ])
            
            return "\n".join(storage_info) if storage_info else "스토리지 정보 없음"
            
        except Exception as e:
            logger.error(f"스토리지 제조사 정보 처리 중 오류: {e}")
            return "스토리지 정보 처리 중 오류"

    # BIOS 설정 포맷팅
    def process_bios_settings(self, bios_data):
        if not isinstance(bios_data, dict):
            return "Invalid BIOS data format"
        
        formatted_settings = [
            "BIOS 설정 정보",
            "=" * 40,
            ""
        ]
        
        # 모든 BIOS 설정을 표시
        for key, value in bios_data.items():
            if key != "Name":  # Name 필드 제외
                formatted_settings.append(f"{key}: {value}")
        
        return "\n".join(formatted_settings)

    # 네트워크 어댑터 정보 포맷팅
    def process_nic_info(self, network_adapters):
        """NIC 정보를 처리합니다."""
        try:
            formatted_settings = [
                "NIC 설정 정보",
                "=" * 40,
                ""
            ]

            for adapter in network_adapters['Members']:
                if 'NetworkDeviceFunctions' in adapter:
                    functions = adapter['NetworkDeviceFunctions']
                    if 'Members' in functions:
                        for func in functions['Members']:
                            if 'Oem' in func and 'Dell' in func['Oem']:
                                dell_attrs = func['Oem']['Dell'].get('DellNetworkAttributes', {})
                                if dell_attrs:
                                    attrs = dell_attrs.get('Attributes', {})
                                    for key, value in sorted(attrs.items()):
                                        formatted_settings.append(f"- {key}: {value}")
                                    formatted_settings.append("")

            return "\n".join(formatted_settings) if formatted_settings else "NIC 정보를 처리할 수 없습니다."
        except Exception as e:
            logger.error(f"NIC 정보 처리 중 오류: {str(e)}")
            return "NIC 정보를 처리할 수 없습니다."

    # 펌웨어 정보 포맷팅
    def process_firmware_details(self, firmware_details):
        try:
            formatted_details = []
            for detail in firmware_details:
                if not detail:
                    continue
                    
                formatted_detail = {
                    'Name': detail.get('Name', '정보없음'),
                    'Id': detail.get('Id', '정보없음'),
                    'Version': detail.get('Version', '정보없음'),
                    'Status': detail.get('Status', {}).get('Health', '정보없음'),
                    'State': detail.get('Status', {}).get('State', '정보없음')
                }
                formatted_details.append(formatted_detail)
            
            if not formatted_details:
                return "설치된 펌웨어 정보가 없습니다."
                
            # 결과를 보기 좋게 포맷팅
            result = ["펌웨어 정보:"]
            # 헤더 추가
            result.extend([
                "=" * 40,
                ""
            ])
            for detail in formatted_details:
                result.append(f"\n이름: {detail['Name']}")
                result.append(f"장치 ID: {detail['Id']}")
                result.append(f"버전: {detail['Version']}")
                result.append(f"상태: {detail['Status']}")
                result.append(f"설치 상태: {detail['State']}")
                result.append("-" * 30)
            
            return "\n".join(result)
            
        except Exception as e:
            logger.error(f"펌웨어 상세 정보 처리 중 오류: {e}")
            return "펌웨어 정보 처리 중 오류가 발생했습니다."

    # 시스템 로그 포맷팅
    def process_system_logs(self, logs):
        log_entries = []
        for entry in logs:
            log_entries.append(
                f"로그 ID: {entry.get('Id', 'N/A')}, "
                f"생성 시간: {entry.get('Created', 'N/A')}, "
                f"메시지: {entry.get('Message', 'N/A')}, "
                f"심각도: {entry.get('Severity', 'N/A')}"
            )
        
        return "\n".join(log_entries)

    def process_smart_logs(self, smart_logs):
        """SMART 로그 데이터를 처리합니다."""
        processed_logs = []
        
        for log in smart_logs:
            drive_info = log.get("DriveInfo", {})
            processed_log = {
                "드라이브 정보": {
                    "이름": drive_info.get("Name", "정보없음"),
                    "모델": drive_info.get("Model", "정보없음"),
                    "시리얼 번호": drive_info.get("SerialNumber", "정보없음")
                },
                "상태 정보": {
                    "수명": self._get_smart_remaining_life(log),
                    "온도": self._get_smart_temperature(log),
                    "읽기 오류율": log.get("ReadErrorRate", "정보없음"),
                    "쓰기 오류율": log.get("WriteErrorRate", "정보없음"),
                    "전원 켜짐 시간": log.get("PowerOnHours", "정보없음"),
                    "미디어 오류": log.get("MediaErrors", "정보없음"),
                    "하드웨어 오류": log.get("HardwareErrors", "정보없음")
                }
            }
            processed_logs.append(processed_log)
        
        return processed_logs

    def _get_smart_remaining_life(self, log):
        """드라이브 잔여 수명을 계산합니다."""
        wear_level = log.get("WearLeveling", {}).get("RemainingLife")
        if wear_level is not None:
            return f"{wear_level}%"
        return "정보없음"

    def _get_smart_temperature(self, log):
        """드라이브 온도를 가져옵니다."""
        temp = log.get("Temperature", {}).get("CurrentTemperature")
        if temp is not None:
            return f"{temp}°C"
        return "정보없음"