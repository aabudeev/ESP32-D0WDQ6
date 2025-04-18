from machine import Pin
import uasyncio as asyncio

class Buttons:
    """
    This class manages the buttons used for controlling elevators and panels.
    It detects button presses and triggers appropriate actions via the WebSocket client (if configured).
    """
    def __init__(self, call_pins, panel_pins, prg_pin):
        """
        Initialize the Buttons instance.

        Args:
            call_pins (list[int]): List of GPIO pin numbers for call buttons.
            panel_pins (list[int]): List of GPIO pin numbers for panel buttons.
            prg_pin (int): GPIO pin number for the programming (PRG) button.
        """
        # Initialize call buttons as input pins with pull-up resistors
        self.call_buttons = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in call_pins]
        # Initialize panel buttons as input pins with pull-up resistors
        self.panel_buttons = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in panel_pins]
        # Initialize the PRG button as an input pin with a pull-up resistor
        self.prg_button = Pin(prg_pin, Pin.IN, Pin.PULL_UP)
        self.ws_client = None  # Placeholder for the WebSocket client instance
        self.current_motor = 0  # Placeholder for the current motor identifier

    def set_ws_client(self, ws_client):
        """
        Link the WebSocket client to the buttons controller.

        Args:
            ws_client (WebSocketClient): The WebSocket client instance to send actions to.
        """
        self.ws_client = ws_client  # Store the WebSocket client reference

    async def is_panel_active_for(self, elevator_id):
        """
        Check if the panel is active for the specified elevator.

        Args:
            elevator_id (int): The ID of the elevator to check.

        Returns:
            bool: True if the panel is active for the elevator, False otherwise.
        """
        return (
            self.ws_client and  # Ensure the WebSocket client is configured
            elevator_id in self.ws_client.active_elevators and  # Check if the elevator is active
            not self.ws_client.active_elevators[elevator_id].done()  # Ensure the task is not completed
        )

    async def run(self):
        """
        Main asynchronous task to monitor button presses and trigger actions.

        This method continuously checks the state of call buttons, panel buttons, 
        and the PRG button. It sends corresponding commands to the WebSocket server.
        """
        while True:
            # Check for call button presses
            for i, button in enumerate(self.call_buttons):
                if button.value() == 0:  # Button is pressed (active-low)
                    print(f"Call button {i+1} pressed (floor {i+1})")
                    # Send a call request to the WebSocket server if configured
                    if self.ws_client:
                        await self.ws_client.send_call(floor=i+1, elevator=i)
                    await asyncio.sleep_ms(300)  # Debounce delay for button press

            # Check for panel button presses associated with active elevators
            if self.ws_client:
                # Get a list of active elevator IDs
                active_elevators = list(getattr(self.ws_client, 'active_elevators', {}).keys())

                for elevator_id in active_elevators:
                    # Check if the panel is active for the current elevator
                    if await self.is_panel_active_for(elevator_id):
                        for i, panel_button in enumerate(self.panel_buttons):
                            if panel_button.value() == 0:  # Button is pressed (active-low)
                                print(f"Panel button {i+1} pressed for elevator {elevator_id}")
                                # Send a task request to the WebSocket server
                                await self.ws_client.send_task(
                                    floor=i+1,  # Floor number
                                    motor=elevator_id  # Elevator ID
                                )
                                await asyncio.sleep_ms(300)  # Debounce delay for button press

            # Check for PRG button press (used for resetting elevators)
            if self.prg_button.value() == 0:  # Button is pressed (active-low)
                print("PRG button pressed - resetting all elevators")
                # Send a reset command to the WebSocket server if configured
                if self.ws_client:
                    await self.ws_client.send_reset()
                await asyncio.sleep_ms(300)  # Debounce delay for button press

            # Short delay for the loop to avoid excess CPU usage
            await asyncio.sleep_ms(50)