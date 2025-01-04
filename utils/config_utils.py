import json
import os
from cryptography.fernet import Fernet
from pathlib import Path
from config.system.log_config import setup_logging

logger = setup_logging()

class ConfigManager:
    def __init__(self):
        self.config_dir = Path(os.path.expanduser("~/.dell_idrac"))
        self.config_file = self.config_dir / "config.enc"
        self.key_file = self.config_dir / "key.bin"
        self._init_encryption()

    def _init_encryption(self):
        self.config_dir.mkdir(exist_ok=True)
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
        self.fernet = Fernet(self.key_file.read_bytes())

    def save_config(self, config_dict):
        encrypted_data = self.fernet.encrypt(json.dumps(config_dict).encode())
        self.config_file.write_bytes(encrypted_data)

    def load_config(self):
        if not self.config_file.exists():
            return {}
        encrypted_data = self.config_file.read_bytes()
        try:
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except:
            return {}
