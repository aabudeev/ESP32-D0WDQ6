from machine import unique_id, freq
from os import uname
from gc import mem_free, mem_alloc

class DeviceInfo:
    @staticmethod
    def get_system_info():
        board_id = ":".join("{:02x}".format(b) for b in unique_id())
        return {
            "Platform": uname()[0],
            "Board": "ESP32-D0WDQ6",
            "Version": uname()[2],
            "Board ID": board_id,
            "CPU frequency": f"{freq() / 1_000_000:.2f} MHz",
            "Allocated memory": f"{mem_alloc() / 1024:.2f} KB",
            "Free memory": f"{mem_free() / 1024:.2f} KB"
        }
