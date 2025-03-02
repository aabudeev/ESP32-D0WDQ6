import ujson
import os
from network import WLAN, STA_IF, AP_IF
from time import sleep_ms
from machine import unique_id

class WiFiManager:
    def __init__(self):
        self.sta = WLAN(STA_IF)
        self.ap = WLAN(AP_IF)
        self.config_file = "wifi_config.json"

    def get_mac_suffix(self):
        """Возвращает последние два октета MAC-адреса."""
        mac = unique_id()
        return "{:02x}{:02x}".format(mac[-2], mac[-1])

    def scan_networks(self):
        """Сканирует доступные Wi-Fi сети."""
        self.sta.active(True)
        networks = self.sta.scan()
        return [network[0].decode() for network in networks]

    def load_config(self):
        """Загружает конфигурацию Wi-Fi из файла."""
        if self.config_file in os.listdir():
            with open(self.config_file, "r") as f:
                return ujson.load(f)
        return None

    def save_config(self, ssid, password):
        """Сохраняет конфигурацию Wi-Fi в файл."""
        with open(self.config_file, "w") as f:
            ujson.dump({"ssid": ssid, "password": password}, f)

    def connect(self, ssid, password, max_attempts=20):
        """Подключается к Wi-Fi сети."""
        self.sta.active(True)
        self.sta.connect(ssid, password)
        for _ in range(max_attempts):
            if self.sta.isconnected():
                return True
            sleep_ms(500)
        return False

    def start_ap(self, ssid, password="waterstd"):
        """Запускает точку доступа."""
        self.ap.active(True)
        self.ap.config(essid=ssid, password=password, authmode=3)
        return self.ap

    def stop_ap(self):
        """Останавливает точку доступа."""
        self.ap.active(False)
