from dataclasses import dataclass
from config.system.log_config import setup_logging

logger = setup_logging()

@dataclass
class URLPattern:
    BASE = "/redfish/v1"
    SYSTEMS = f"{BASE}/Systems/System.Embedded.1"
    CHASSIS = f"{BASE}/Chassis/System.Embedded.1"
    MANAGERS = f"{BASE}/Managers/iDRAC.Embedded.1"
    UPDATE = f"{BASE}/UpdateService"
    
    # 시스템 관련 엔드포인트
    SYSTEM_BIOS = f"{SYSTEMS}/Bios"
    SYSTEM_PROCESSORS = f"{SYSTEMS}/Processors"
    SYSTEM_MEMORY = f"{SYSTEMS}/Memory"
    SYSTEM_STORAGE = f"{SYSTEMS}/Storage"
    SYSTEM_STORAGE_DRIVES = f"{SYSTEM_STORAGE}/{{controller_id}}/Drives"
    SYSTEM_STORAGE_DRIVE = f"{SYSTEM_STORAGE}/{{controller_id}}/Drives/{{drive_id}}"    

    # 섀시 관련 엔드포인트
    CHASSIS_THERMAL = f"{CHASSIS}/Thermal"
    CHASSIS_POWER = f"{CHASSIS}/Power"
    CHASSIS_NETWORK = f"{CHASSIS}/NetworkAdapters"

    NETWORK_ADAPTER = f"{CHASSIS_NETWORK}/{{adapter_id}}"
    NETWORK_PORTS = f"{CHASSIS_NETWORK}/{{adapter_id}}/NetworkPorts"
    NETWORK_DEVICE_FUNCTIONS = f"{CHASSIS_NETWORK}/{{adapter_id}}/NetworkDeviceFunctions"   
    DELL_NETWORK_ATTRIBUTES = f"{CHASSIS_NETWORK}/{{adapter_id}}/NetworkDeviceFunctions/{{func_id}}/Oem/Dell/DellNetworkAttributes"

    # 로그 서비스 관련 엔드포인트
    MANAGER_SEL_LOG = f"{MANAGERS}/LogServices/Sel"
    MANAGER_SEL_ENTRIES = f"{MANAGERS}/LogServices/Sel/Entries"
    MANAGER_LC_LOG = f"{MANAGERS}/LogServices/Lclog"
    MANAGER_LC_ENTRIES = f"{MANAGERS}/LogServices/Lclog/Entries"
    MANAGER_SEL_CLEAR = f"{MANAGERS}/LogServices/Sel/Actions/LogService.ClearLog"

    # GPU 관련 엔드포인트
    SYSTEM_GPU = f"{SYSTEMS}/Processors"
    SYSTEM_PCIE_DEVICES = f"{SYSTEMS}/PCIeDevices"
    SYSTEM_PCIE_FUNCTIONS = f"{SYSTEMS}/PCIeFunctions"

    # LICENSE 관련 엔드포인트
    LICENSE_INFO = f"{MANAGERS}/Oem/Dell/DellLicenses"

    # 펌웨어 관련 엔드포인트 추가
    FIRMWARE_INVENTORY = f"{UPDATE}/FirmwareInventory"
    FIRMWARE_INVENTORY_COMPONENTS = f"{UPDATE}/FirmwareInventory/{{component_id}}"

    # iDRAC 관련 엔드포인트
    IDRAC_MAC_ADDRESS = f"{MANAGERS}/Oem/Dell/DellAttributes/iDRAC.Embedded.1"
    IDRAC_INFO = f"{MANAGERS}/Oem/Dell/DellAttributes/iDRAC.Embedded.1"
    IDRAC_PWR_INFO = f"{MANAGERS}/Oem/Dell/DellAttributes/System.Embedded.1"

    # 네트워크 어댑터 관련 엔드포인트 추가
    NETWORK_ADAPTER_ATTRIBUTES = f"{CHASSIS_NETWORK}/{{adapter_id}}/NetworkDeviceFunctions/{{func_id}}/Oem/Dell/DellNetworkAttributes/{{func_id}}"
    NETWORK_ATTRIBUTES_REGISTRY = f"{BASE}/Registries/NetworkAttributesRegistry_{{func_id}}"

    # TSR 로그 관련 엔드포인트 추가
    TSR_EXPORT = f"{MANAGERS}/Oem/Dell/DellLCService/Actions/DellLCService.ExportTechSupportReport"

    # JobService 관련 엔드포인트 추가
    JOB_SERVICE = f"{BASE}/JobService"
    JOB_COLLECTION = f"{JOB_SERVICE}/Jobs"
    JOB_DETAILS = f"{JOB_COLLECTION}/{{job_id}}"

class RedfishEndpoints:
    def __init__(self, ip: str, port: str = "443"):
        """
        Args:
            ip (str): iDRAC IP 주소
            port (str, optional): iDRAC 포트 번호. 기본값은 "443"
        """
        self.base_url = f"https://{ip}:{port}"
    
    def get_url(self, pattern: str) -> str:
        """URL 패턴에 base_url을 결합하여 완전한 URL 반환"""
        full_url = f"{self.base_url}{pattern}"
        
        # Storage 관련 패턴 확인
        if 'Storage' in pattern and 'Drives' in pattern:
            if 'drive_id' in pattern:
                purpose = '특정 스토리지 드라이브 상태 조회'
            else:
                purpose = '스토리지 드라이브 상태 조회'
        else:
            purpose = {
                # 시스템 관련
                '/redfish/v1/Systems/System.Embedded.1': '시스템 기본 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/Bios': 'BIOS 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/Processors': 'CPU/GPU 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/Memory': '메모리 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/Storage': '스토리지 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/PCIeDevices': 'PCIe 장치 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/PCIeFunctions': 'PCIe 기능 정보 조회',
                
                # 섀시 관련
                '/redfish/v1/Chassis/System.Embedded.1/Thermal': '온도 정보 조회',
                '/redfish/v1/Chassis/System.Embedded.1/Power': '전원 상태 조회',
                '/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters': '네트워크 어댑터 정보 조회',
                
                # 네트워크 관련
                '/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/{adapter_id}': '특정 네트워크 어댑터 정보 조회',
                '/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/{adapter_id}/NetworkPorts': '네트워크 포트 정보 조회',
                '/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/{adapter_id}/NetworkDeviceFunctions': '네트워크 장치 기능 정보 조회',
                '/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/{adapter_id}/NetworkDeviceFunctions/{func_id}/Oem/Dell/DellNetworkAttributes': 'Dell 네트워크 어댑터 기능 정보 조회',
                
                # iDRAC 관련
                '/redfish/v1/Managers/iDRAC.Embedded.1': 'iDRAC 정보 조회',
                '/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1': 'iDRAC 상세 정보 조회',
                '/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLicenses': 'iDRAC 라이선스 정보 조회',
                
                # 로그 서비스 관련
                '/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel': 'SEL 로그 서비스 조회',
                '/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Entries': 'SEL 로그 엔트리 조회',
                '/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Actions/LogService.ClearLog': 'SEL 로그 클리어',
                '/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog': 'LC 로그 서비스 조회',
                '/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries': 'LC 로그 엔트리 조회',
                
                # 업데이트 서비스
                '/redfish/v1/UpdateService': '업데이트 서비스 조회',
                '/redfish/v1/UpdateService/FirmwareInventory': '펌웨어 인벤토리 조회',
                '/redfish/v1/UpdateService/FirmwareInventory/{component_id}': '펌웨어 인벤토리 조회',
                
                # GPU 관련
                '/redfish/v1/Systems/System.Embedded.1/Processors': 'CPU/GPU 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/PCIeDevices': 'GPU 독립 정보 조회',
                '/redfish/v1/Systems/System.Embedded.1/PCIeFunctions': 'GPU 기능 정보 조회',

                # License 관련
                '/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLicenses': 'License 정보 조회',

                # 펌웨어 관련
                '/redfish/v1/UpdateService/FirmwareInventory': '펌웨어 인벤토리 조회',
                '/redfish/v1/UpdateService/FirmwareInventory/{component_id}': '펌웨어 인벤토리 조회',

                # TSR LOG 수집 관련
                '/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLCService/Actions/DellLCService.ExportTechSupportReport': 'TSR 로그 수집',

            }.get(pattern, '알 수 없는 요청')
        
        logger.debug(f"Redfish API 요청: {purpose} - URL: {full_url}")
        return full_url

    # 시스템 엔드포인트
    @property
    def system(self) -> str:
        """시스템 기본 정보 조회"""
        return self.get_url(URLPattern.SYSTEMS)
    
    @property
    def processors(self) -> str:
        """프로세서 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_PROCESSORS)
    
    @property
    def memory(self) -> str:
        """메모리 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_MEMORY)
    
    @property
    def storage(self) -> str:
        """스토리지 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_STORAGE)

    def get_storage_drives_url(self, controller_id: str) -> str:
        """특정 컨트롤러의 스토리지 드라이브 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_STORAGE_DRIVES.format(controller_id=controller_id))
    
    def get_storage_drive_url(self, controller_id: str, drive_id: str) -> str:
        """특정 컨트롤러의 특정 드라이브 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_STORAGE_DRIVE.format(
            controller_id=controller_id, 
            drive_id=drive_id
        ))

    @property
    def bios(self) -> str:
        """BIOS 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_BIOS)

    @property
    def idrac_info(self) -> str:
        """iDRAC 정보 조회"""
        return self.get_url(URLPattern.IDRAC_INFO)

    @property
    def idrac_pwr_info(self) -> str:
        """iDRAC PWR 정보 조회"""
        return self.get_url(URLPattern.IDRAC_PWR_INFO)

    # 섀시 엔드포인트
    @property
    def chassis(self) -> str:
        """섀시 정보 조회"""
        return self.get_url(URLPattern.CHASSIS)
    
    @property
    def thermal(self) -> str:
        """열 정보 조회"""
        return self.get_url(URLPattern.CHASSIS_THERMAL)
    
    @property
    def power(self) -> str:
        """전원 정보 조회"""
        return self.get_url(URLPattern.CHASSIS_POWER)
    
    @property
    def network_adapters(self) -> str:
        """네트워크 어댑터 정보 조회"""
        return self.get_url(URLPattern.CHASSIS_NETWORK)

    def get_network_adapter_url(self, adapter_id: str) -> str:
        """특정 네트워크 어댑터 정보 조회"""
        return self.get_url(URLPattern.NETWORK_ADAPTER.format(adapter_id=adapter_id))

    def get_network_ports_url(self, adapter_id: str) -> str:
        """네트워크 포트 정보 조회"""
        return self.get_url(URLPattern.NETWORK_PORTS.format(adapter_id=adapter_id))

    def get_network_device_functions_url(self, adapter_id: str) -> str:
        """네트워크 장치 기능 정보 조회"""
        return self.get_url(URLPattern.NETWORK_DEVICE_FUNCTIONS.format(adapter_id=adapter_id))

    def get_dell_network_attributes_url(self, adapter_id: str, func_id: str) -> str:
        """Dell 네트워크 어댑터 기능 정보 조회"""
        return self.get_url(URLPattern.DELL_NETWORK_ATTRIBUTES.format(adapter_id=adapter_id, func_id=func_id))
    
    # 로그 엔드포인트
    @property
    def sel_log_service(self) -> str:
        """SEL 로그 서비스 정보 조회"""
        return self.get_url(URLPattern.MANAGER_SEL_LOG)
    
    @property
    def sel_entries(self) -> str:
        """SEL 로그 엔트리 조회"""
        return self.get_url(URLPattern.MANAGER_SEL_ENTRIES)
    
    @property
    def lc_log_service(self) -> str:
        """LC 로그 서비스 정보 조회"""
        return self.get_url(URLPattern.MANAGER_LC_LOG)
    
    @property
    def lc_entries(self) -> str:
        """LC 로그 엔트리 조회"""
        return self.get_url(URLPattern.MANAGER_LC_ENTRIES)
    
    @property
    def clear_sel_log(self) -> str:
        """SEL 로그 클리어 액션 URL"""
        return self.get_url(URLPattern.MANAGER_SEL_CLEAR)
    
    # 업데이트 서비스 관련 엔드포인트
    @property
    def update_service(self) -> str:
        """업데이트 서비스 정보 조회"""
        return self.get_url(URLPattern.UPDATE)

    @property
    def firmware_inventory(self) -> str:
        """펌웨어 인벤토리 정보 조회"""
        return self.get_url(URLPattern.FIRMWARE_INVENTORY)

    def get_firmware_inventory_component_url(self, component_id: str) -> str:
        """특정 펌웨어 인벤토리 정보 조회"""
        return self.get_url(URLPattern.FIRMWARE_INVENTORY_COMPONENTS.format(component_id=component_id))

    @property
    def managers(self) -> str:
        """매니저 정보 조회"""
        return self.get_url(URLPattern.MANAGERS)

    # GPU 관련 엔드포인트
    def get_gpu_url(self, gpu_id: str) -> str:
        """특정 GPU 정보 조회"""
        return self.get_url(f"{URLPattern.SYSTEM_GPU}/{gpu_id}")

    def get_pcie_device_url(self, device_id: str) -> str:
        """특정 PCIe 장치 정보 조회"""
        return self.get_url(f"{URLPattern.SYSTEM_PCIE_DEVICES}/{device_id}")

    def get_pcie_function_url(self, function_id: str) -> str:
        """특정 PCIe 기능 정보 조회"""
        return self.get_url(f"{URLPattern.SYSTEM_PCIE_FUNCTIONS}/{function_id}")

    @property
    def gpu(self) -> str:
        """GPU 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_GPU)

    @property
    def pcie_devices(self) -> str:
        """PCIe 장치 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_PCIE_DEVICES)

    @property
    def pcie_functions(self) -> str:
        """PCIe 기능 정보 조회"""
        return self.get_url(URLPattern.SYSTEM_PCIE_FUNCTIONS)

    @property
    def gpu_thermal(self) -> str:
        """GPU 온도 정보 조회"""
        return self.get_url(f"{URLPattern.CHASSIS_THERMAL}/GPU")

    @property
    def gpu_power(self) -> str:
        """GPU 전원 상태 조회"""
        return self.get_url(f"{URLPattern.CHASSIS_POWER}/GPU")

    @property
    def gpu_event_logs(self) -> str:
        """GPU 이벤트 로그 조회"""
        return self.get_url(f"{URLPattern.MANAGER_SEL_LOG}/GPU")

    # LICENSE 관련 엔드포인트
    @property
    def license_info(self) -> str:
        """라이선스 정보 조회"""
        return self.get_url(URLPattern.LICENSE_INFO)

    @property
    def idrac_mac_address(self) -> str:
        """iDRAC MAC 주소 조회"""
        return self.get_url(URLPattern.IDRAC_MAC_ADDRESS)

    def get_network_adapter_attributes_url(self, adapter_id: str, func_id: str) -> str:
        """네트워크 어댑터 속성 조회"""
        pattern = URLPattern.NETWORK_ADAPTER_ATTRIBUTES.format(
            adapter_id=adapter_id,
            func_id=func_id
        )
        return self.get_url(pattern)
    
    def get_network_attributes_registry_url(self, func_id: str) -> str:
        """네트워크 속성 레지스트리 조회"""
        pattern = URLPattern.NETWORK_ATTRIBUTES_REGISTRY.format(
            func_id=func_id
        )
        return self.get_url(pattern)

    # JobService 관련 메서드 추가
    @property
    def job_service(self) -> str:
        """JobService 정보 조회"""
        return self.get_url(URLPattern.JOB_SERVICE)

    @property
    def job_collection(self) -> str:
        """Job 컬렉션 조회"""
        return self.get_url(URLPattern.JOB_COLLECTION)

    def get_job_details_url(self, job_id: str) -> str:
        """특정 Job 상세 정보 조회"""
        return self.get_url(URLPattern.JOB_DETAILS.format(job_id=job_id))