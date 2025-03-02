import uasyncio as asyncio
from wifi_manager import WiFiManager
from device_info import DeviceInfo
from led_manager import LEDManager
from elevator import Elevator

async def main():
    # Инициализация компонентов
    wifi = WiFiManager()
    led = LEDManager()
    elevator = Elevator()

    # Подключение к Wi-Fi
    config = wifi.load_config()
    if config:
        if not wifi.connect(config["ssid"], config["password"], max_attempts=5):
            print("Failed to connect. Rebooting...")
            import machine
            machine.reset()

    # Мигаем светодиодом раз в секунду
    asyncio.create_task(led.blink(1000))

    # Запуск задач для лифтов
    asyncio.create_task(elevator.handle_external_buttons())
    asyncio.create_task(elevator.handle_lifts())
    asyncio.create_task(elevator.handle_prg_button())
    asyncio.create_task(elevator.blink())

    # Вывод информации о системе и сети
    device = DeviceInfo()
    print("System Info:")
    for key, value in device.get_system_info().items():
        print(f"  {key}: {value}")

    print("Network Info:")
    for key, value in device.get_network_info(wifi.sta).items():
        print(f"  {key}: {value}")

    # Бесконечный цикл для поддержания работы программы
    while True:
        await asyncio.sleep(1)

# Запуск основной функции
asyncio.run(main())