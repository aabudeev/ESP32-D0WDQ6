import machine
import uasyncio as asyncio
from wifi import WiFiAP, WiFiClient
from motor import MotorController
from led import LEDController
from websocket import WebSocketServer
from pairing import Pairing
from elevator import ElevatorManager

# Configuration constants
CLIENT_MAC_ADDR = "3c71bf5a5414"  # MAC address suffix for client identification
AP_SSID = "ESP32-D0WDQ6"          # Base SSID for access point
AP_PASSWORD = "waterstd"          # Password for access point

GUEST_WIFI = False                # Flag to choose between AP mode or connecting to guest WiFi
GUEST_SSID = "SSID"               # Guest WiFi SSID
GUEST_PASSWORD = "p@$$w0rd"       # Guest WiFi password

LED_PIN = 2                       # Pin for onboard LED
MOTOR_PINS = [                    # Pins for 3 motors (STEP, DIR, ENABLE)
    (21, 13, 12),  # Motor 1
    (14, 27, 26),  # Motor 2
    (25, 15, 32)   # Motor 3
]

# Initialize components
led = LEDController(LED_PIN)
motors = MotorController(MOTOR_PINS)
elevator = ElevatorManager(motors)
wifi_ap = WiFiAP(led)
wifi_client = WiFiClient(led)
ws_server = WebSocketServer(motors, led, wifi_ap, elevator)
pairing = None

async def main():
    """Main coroutine that initializes and manages all system components."""
    global pairing

    # Generate unique identifiers based on hardware MAC
    mac = machine.unique_id()
    mac_suffix = ''.join(['{:02x}'.format(b) for b in mac[-2:]])
    ssid = f"{AP_SSID}-{mac_suffix}"
    hostname = f"esp32-{mac_suffix}"

    # Start LED controller task
    asyncio.create_task(led.run())

    if GUEST_WIFI:
        # Connect to guest WiFi network
        led.set_mode("wifi_connect")
        await wifi_client.connect(GUEST_SSID, GUEST_PASSWORD)
        if wifi_client.is_connected():
            led.set_mode("connecting")
            ip = wifi_client.get_ip()
            print(f"Connected to {GUEST_SSID}")
            print(f"Server IP: {ip}")

            # Start pairing process
            pairing = Pairing(hostname, ip, led)
            await pairing.start()
        else:
            led.set_mode("error")
            print(f"Failed to connect to {GUEST_SSID}")
    else:
        # Start access point
        led.set_mode("wifi_connect")
        await wifi_ap.start(ssid, AP_PASSWORD)
        led.set_mode("connecting")
        ip = wifi_ap.get_ip()
        print(f"Access Point started with SSID: {ssid}")
        print(f"Server IP: {ip}")

        # Start pairing process
        pairing = Pairing(hostname, ip, led)
        await pairing.start()

    # Start WebSocket server
    asyncio.create_task(ws_server.start())

    # Main monitoring loop
    while True:
        if GUEST_WIFI:
            # Reconnect if guest WiFi connection is lost
            if not wifi_client.is_connected():
                led.set_mode("not_connected")
                print("Lost connection to guest WiFi")
                await wifi_client.connect(GUEST_SSID, GUEST_PASSWORD)
        else:
            # Check for connected clients in AP mode
            if wifi_ap.check_client_connected():
                if not ws_server.client_connected:
                    led.set_mode("connecting")
            else:
                led.set_mode("not_connected")

        await asyncio.sleep(1)

# Start the main coroutine
asyncio.run(main())