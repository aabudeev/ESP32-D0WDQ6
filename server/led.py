from machine import Pin
import uasyncio as asyncio

class LEDController:
    """
    A controller class for managing LED behavior to reflect system states.
    """

    def __init__(self, pin: int):
        """
        Initialize the LED controller.

        Args:
            pin: GPIO pin number connected to the LED.
        """
        self.led = Pin(pin, Pin.OUT)
        self.mode: str = "idle"
        self.led.value(0)  # Turn LED off initially

    async def run(self):
        """
        Main loop to update LED state based on current mode.
        This function should be run as an asyncio task.
        """
        while True:
            if self.mode == "not_connected":
                # Fast blink: Not connected to Wi-Fi
                self.led.value(not self.led.value())
                await asyncio.sleep_ms(100)

            elif self.mode == "wifi_connect":
                # Fast blink: Connecting to Wi-Fi
                self.led.value(not self.led.value())
                await asyncio.sleep_ms(100)

            elif self.mode == "pairing":
                # Triple blink: In pairing mode
                for _ in range(3):
                    self.led.value(1)
                    await asyncio.sleep_ms(100)
                    self.led.value(0)
                    await asyncio.sleep_ms(100)
                await asyncio.sleep_ms(1000)

            elif self.mode == "connecting":
                # Medium blink: Connecting to client
                self.led.value(not self.led.value())
                await asyncio.sleep_ms(500)

            elif self.mode == "connected":
                # Solid ON: Fully connected
                self.led.value(1)
                await asyncio.sleep_ms(100)

            await asyncio.sleep(0)  # Yield control to the event loop

    def set_mode(self, mode: str):
        """
        Set the current LED mode.

        Args:
            mode: One of the supported mode strings (e.g., "not_connected", "connected", etc.)
        """
        print(f"LED mode: {mode}")
        self.mode = mode