from dataclasses import dataclass

@dataclass
class IDRACConfig:
    NAME: str = ""
    IP: str = ""
    PORT: str = ""
    USERNAME: str = ""
    PASSWORD: str = ""

    def update(self, ip="", username="", password="", name="", port=""):
        self.NAME = name
        self.IP = ip
        self.PORT = port
        self.USERNAME = username
        self.PASSWORD = password

    def __str__(self):
        return f"{self.NAME}: {self.IP}"