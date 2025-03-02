import uasyncio as asyncio
from wifi_manager import WiFiManager
from web_server import WebServer
from led_manager import LEDManager
import machine
import socket

async def boot():
    wifi = WiFiManager()
    led = LEDManager()
    asyncio.create_task(led.blink(100))  # Мигаем светодиодом

    config = wifi.load_config()
    networks = wifi.scan_networks()

    if not config:
        # Если файла конфигурации нет, запускаем точку доступа
        ap_ssid = f"ESP32-D0WDQ6-{wifi.get_mac_suffix()}"
        wifi.start_ap(ap_ssid)
        print(f"Access point started. SSID: {ap_ssid}")

        # Запускаем веб-сервер для получения данных от пользователя
        server = WebServer(wifi)
        print("Web server started. Waiting for user input...")
        await server.start()

        # После получения данных от пользователя, подключаемся к пользовательской сети
        if wifi.connect(config["ssid"], config["password"]):
            print("Connected to user Wi-Fi!")
            ip_address = wifi.sta.ifconfig()[0]  # Получаем IP-адрес в пользовательской сети
            print(f"IP address in user network: {ip_address}")

            # Гасим пользовательскую Wi-Fi сеть
            wifi.sta.disconnect()
            print("Disconnected from user Wi-Fi.")

            # Переподнимаем нашу точку доступа для редиректа
            wifi.start_ap(ap_ssid)
            print("Access point restarted for redirect.")

            # Перенаправляем пользователя на новый IP-адрес
            redirect_response = server.redirect_to_user_network(ip_address)

            # Отправляем ответ с перенаправлением
            addr = socket.getaddrinfo('192.168.4.1', 80)[0][-1]
            s = socket.socket()
            s.bind(addr)
            s.listen(1)
            conn, addr = s.accept()
            conn.send(redirect_response)
            conn.close()

            # Перезагружаем контроллер
            print("Rebooting to switch to user network...")
            machine.reset()
        else:
            print("Failed to connect to user Wi-Fi. Restarting setup...")
            machine.reset()
    else:
        # Если файл конфигурации есть, проверяем, совпадает ли SSID с доступными сетями
        if config["ssid"] in networks:
            print("SSID in config matches available networks. Exiting boot.py.")
            return  # Выходим из boot.py, main.py сам подключится
        else:
            # Если SSID не совпадает, запускаем точку доступа для повторной настройки
            print("SSID in config does not match available networks. Starting AP...")
            ap_ssid = f"ESP32-D0WDQ6-{wifi.get_mac_suffix()}"
            wifi.start_ap(ap_ssid)
            server = WebServer(wifi)
            await server.start()

asyncio.run(boot())