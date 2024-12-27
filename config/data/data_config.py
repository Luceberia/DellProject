from dataclasses import dataclass

@dataclass
class DataTypes:
    PART_STATUS: str = "PART_STATUS"
    MANUFACTURER: str = "MANUFACTURER"
    BIOS: str = "BIOS"
    NIC: str = "NIC"
    FW: str = "F/W"

@dataclass
class CommonFields:
    NAME: str = "Name"
    STATUS: str = "Status"
    HEALTH: str = "Health"
    MODEL: str = "Model"
    CAPACITY: str = "Capacity"
    MANUFACTURER: str = "Manufacturer"