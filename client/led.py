from machine import Pin
import uasyncio as asyncio

class LEDController:
    """
    This class manages a single LED and provides functionality to control its behavior based on different modes.
    The LED can blink, stay on, or turn off depending on the current mode.
    """
    def __init__(self, pin):
        """
        Initialize the LEDController instance.
        
        Args:
            pin (int): The GPIO pin number to which the LED is connected.
        """
        self.led = Pin(pin, Pin.OUT)  # Initialize the pin as an output pin for controlling the LED
        self.mode = "idle"  # Default mode is "idle", where the LED remains off
        self.led.value(0)  # Turn off the LED initially

    async def run(self):
        """
        Main asynchronous task to control the LED behavior based on the current mode.
        This method runs indefinitely and adjusts the LED state dynamically.
        """
        print("LED task started")  # Log the start of the LED task
        while True:
            # LED behavior for different modes
            if self.mode == "wifi_connect":
                # Blink the LED rapidly (100ms interval) to indicate Wi-Fi connection attempts
                self.led.value(not self.led.value())  # Toggle the LED state
                await asyncio.sleep_ms(100)  # Wait for 100 milliseconds
            elif self.mode == "pairing":
                # Blink the LED three times quickly, then pause for 1 second to indicate pairing mode
                for _ in range(3):
                    self.led.value(1)  # Turn on the LED
                    await asyncio.sleep_ms(100)  # Wait for 100 milliseconds
                    self.led.value(0)  # Turn off the LED
                    await asyncio.sleep_ms(100)  # Wait for 100 milliseconds
                await asyncio.sleep_ms(1000)  # Pause for 1 second
            elif self.mode == "connecting":
                # Blink the LED with a 500ms interval to indicate a connection attempt
                self.led.value(not self.led.value())  # Toggle the LED state
                await asyncio.sleep_ms(500)  # Wait for 500 milliseconds
            elif self.mode == "connected":
                # Keep the LED on continuously to indicate a successful connection
                self.led.value(1)  # Turn on the LED
                await asyncio.sleep_ms(100)  # Short delay to avoid task overload
            elif self.mode == "not_connected":
                # Blink the LED rapidly (100ms interval) to indicate a disconnection or error state
                self.led.value(not self.led.value())  # Toggle the LED state
                await asyncio.sleep_ms(100)  # Wait for 100 milliseconds
            await asyncio.sleep(0)  # Yield control to other tasks in the event loop

    def set_mode(self, mode):
        """
        Set the mode for the LED behavior.

        Args:
            mode (str): The mode to set. Possible values are:
                - "wifi_connect": Rapid blinking for Wi-Fi connection attempts.
                - "pairing": Fast triple blink followed by a pause, indicating pairing mode.
                - "connecting": 500ms blink interval for connection attempts.
                - "connected": LED stays on to indicate a successful connection.
                - "not_connected": Rapid blinking for disconnection or error states.
                - "idle": LED stays off.
        """
        print(f"LED mode: {mode}")  # Log the mode change
        self.mode = mode  # Update the mode

class ExtendedLEDs:
    """
    This class manages multiple LEDs for specific functionalities, such as call LEDs and panel LEDs.
    It provides methods to control individual LEDs or reset all LEDs to an off state.
    """
    def __init__(self, call_pins, panel_pins):
        """
        Initialize the ExtendedLEDs instance with call and panel LEDs.

        Args:
            call_pins (list): A list of GPIO pin numbers for call LEDs.
            panel_pins (list): A list of GPIO pin numbers for panel LEDs.
        """
        # Initialize call LEDs as output pins and set their initial state to off
        self.call_leds = [Pin(pin, Pin.OUT, value=0) for pin in call_pins]
        # Initialize panel LEDs as output pins and set their initial state to off
        self.panel_leds = [Pin(pin, Pin.OUT, value=0) for pin in panel_pins]
        self.blink_task = None  # Placeholder for running blink tasks

    async def blink_call_led(self, floor, times=3, interval_ms=500):
        """
        Blink a specific call LED associated with a floor.

        Args:
            floor (int): The floor number (1-based index) to blink the corresponding call LED.
            times (int): The number of times the LED should blink (default: 3).
            interval_ms (int): The duration (in milliseconds) for each blink (default: 500ms).
        """
        if 1 <= floor <= len(self.call_leds):  # Ensure the floor number is valid
            led_index = floor - 1  # Calculate the LED index (0-based)
            for _ in range(times):  # Blink the LED the specified number of times
                self.call_leds[led_index].on()  # Turn on the LED
                await asyncio.sleep_ms(interval_ms)  # Wait for the specified interval
                self.call_leds[led_index].off()  # Turn off the LED
                await asyncio.sleep_ms(interval_ms)  # Wait for the specified interval

    async def blink_panel_led(self, floor, times=3, interval_ms=500):
        """
        Blink a specific panel LED associated with a floor.

        Args:
            floor (int): The floor number (1-based index) to blink the corresponding panel LED.
            times (int): The number of times the LED should blink (default: 3).
            interval_ms (int): The duration (in milliseconds) for each blink (default: 500ms).
        """
        if 1 <= floor <= len(self.panel_leds):  # Ensure the floor number is valid
            led_index = floor - 1  # Calculate the LED index (0-based)
            for _ in range(times):  # Blink the LED the specified number of times
                self.panel_leds[led_index].on()  # Turn on the LED
                await asyncio.sleep_ms(interval_ms)  # Wait for the specified interval
                self.panel_leds[led_index].off()  # Turn off the LED
                await asyncio.sleep_ms(interval_ms)  # Wait for the specified interval

    def reset_all(self):
        """
        Turn off all LEDs (both call and panel LEDs) to reset their states.
        """
        for led in self.call_leds + self.panel_leds:  # Iterate through all LEDs
            led.off()  # Turn off each LED