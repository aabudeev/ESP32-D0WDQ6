from machine import Pin
from time import sleep_ms

class LEDManager:
    def __init__(self, pin=2):
        self.led = Pin(pin, Pin.OUT)

    async def blink(self, interval_ms=100):
        """Мигает светодиодом с заданным интервалом."""
        while True:
            self.led.value(not self.led.value())
            sleep_ms(interval_ms)
