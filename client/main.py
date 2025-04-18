import uasyncio as asyncio
from wifi import WiFiClient
from pairing import Pairing
from websocket import WebSocketClient
from led import LEDController, ExtendedLEDs
from buttons import Buttons
from buzzer import Buzzer

# Define the MAC address of the server for identification purposes
SERVER_MAC_ADDR = "a4cf12259774"

# Access point credentials for fallback Wi-Fi connection in case of no direct network access
AP_SSID = "ESP32-D0WDQ6"
AP_PASSWORD = "waterstd"

# Configuration for guest Wi-Fi network
GUEST_WIFI = False          # Whether to use guest Wi-Fi
GUEST_SSID = "SSID"         # Guest WiFi SSID
GUEST_PASSWORD = "p@$$w0rd" # Guest WiFi password

# GPIO pin for the primary LED indicator
LED_PIN = 2

# GPIO pins for the call LEDs (indicating call statuses)
CALL_LED_PINS = [16, 17, 4]

# GPIO pins for the panel LEDs (indicating panel statuses)
PANEL_LED_PINS = [5, 18, 23]

# GPIO pins for the call buttons (used for user actions on call devices)
CALL_BUTTON_PINS = [21, 13, 12]

# GPIO pins for the panel buttons (used for user actions on panel devices)
PANEL_BUTTON_PINS = [14, 27, 25]

# GPIO pin for the programming button
PRG_PIN = 0

# GPIO pin for the buzzer (used for audio feedback)
BUZZER_PIN = 19

# Initialize the LED controller for managing the main LED
led = LEDController(LED_PIN)

# Initialize the extended LED controller for managing additional LEDs
ext_leds = ExtendedLEDs(CALL_LED_PINS, PANEL_LED_PINS)

# Initialize the button controller for handling button inputs
buttons = Buttons(CALL_BUTTON_PINS, PANEL_BUTTON_PINS, PRG_PIN)

# Initialize the buzzer controller for managing sound feedback
buzzer = Buzzer(BUZZER_PIN)

# Initialize the Wi-Fi client for managing network connectivity
wifi_client = WiFiClient(led)

# Placeholder variables for pairing and WebSocket client instances
pairing = None
ws_client = None

# Main asynchronous function to orchestrate the program execution
async def main():
    global pairing, ws_client  # Use global variables for pairing and WebSocket client

    # Start the LED task to handle LED animations and states
    print("Starting LED task...")
    asyncio.create_task(led.run())

    # Set the LED mode to indicate Wi-Fi connection status
    led.set_mode("wifi_connect")

    # Attempt to connect to Wi-Fi using provided credentials
    if not await wifi_client.connect_to_server(
        GUEST_WIFI, GUEST_SSID, GUEST_PASSWORD, AP_SSID, AP_PASSWORD, SERVER_MAC_ADDR[-4:]
    ):
        # If the connection fails, print an error message and exit
        print("Failed to connect to Wi-Fi")
        return

    # Set the LED to pairing mode to indicate that pairing is in progress
    led.set_mode("pairing")

    # Initialize the pairing process
    pairing = Pairing(led)
    server_ip = await pairing.start()

    # If pairing fails, print an error, set the LED to a "not connected" state, and exit
    if not server_ip:
        print("Failed to pair with server")
        led.set_mode("not_connected")
        return

    # Wait for the server to be ready before proceeding
    print("Waiting for server to be ready...")
    await asyncio.sleep(2)

    # Set the LED to indicate the WebSocket connection is being established
    led.set_mode("connecting")

    # Initialize the WebSocket client with the server IP and other hardware controllers
    ws_client = WebSocketClient(server_ip, led, buttons, buzzer, ext_leds)

    # Link the WebSocket client to the button controller for handling button events
    buttons.set_ws_client(ws_client)
    
    # Start the button task to handle button presses
    print("Starting buttons task...")
    asyncio.create_task(buttons.run())
    
    try:
        # Attempt to start the WebSocket connection
        if not await ws_client.start():
            # If the connection fails, print an error, set the LED to "not connected," and exit
            print("Failed to connect to WebSocket")
            led.set_mode("not_connected")
            return
    except Exception as e:
        # Handle any WebSocket connection errors
        print(f"WebSocket connection error: {e}")
        led.set_mode("not_connected")
        return

    # Main loop to keep the program running
    while True:
        await asyncio.sleep(1)

# Run the main function using the asyncio event loop
asyncio.run(main())
