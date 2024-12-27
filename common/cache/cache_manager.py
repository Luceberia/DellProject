import time
from typing import Dict, Any, Optional

class SystemInfoCache:
    def __init__(self, server_manager):
        self.cache_manager = CacheManager()
        self.server_manager = server_manager
        
    def get_system_info(self, server_ip: str, force_refresh: bool = False) -> dict:
        cache_key = f"{server_ip}_system_info"
        
        if not force_refresh:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data
        
        # 데이터 로드를 병렬로 처리
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_data = {
                'processors': executor.submit(self.server_manager.fetch_processors_info),
                'memory': executor.submit(self.server_manager.fetch_memory_info),
                'storage': executor.submit(self.server_manager.fetch_storage_info),
                'nic': executor.submit(self.server_manager.fetch_network_adapters_info),
                'psu': executor.submit(self.server_manager.fetch_psu_info),
                'idrac': executor.submit(self.server_manager.fetch_detailed_info, 
                                       self.server_manager.endpoints.idrac_mac_address),
                'license': executor.submit(self.server_manager.check_idrac_license)
            }
            
            data = {}
            for key, future in future_to_data.items():
                try:
                    data[key] = future.result()
                except Exception as e:
                    logger.error(f"{key} 데이터 로드 실패: {str(e)}")
                    data[key] = None
        
        self.cache_manager.set(cache_key, data)
        return data
