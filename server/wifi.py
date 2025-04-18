import network
import uasyncio as asyncio

class WiFiAP:
    def __init__(self, led):
        """Initialize WiFi in Access Point mode.
        
        Args:
            led (LEDController): controls the LED (connection status).
        """
        self.led = led
        self.ap = network.WLAN(network.AP_IF)  # Access Point interface
        self.client_connected = False  # Flag indicating client presence

    async def start(self, ssid, password):
        """Start the access point with the given SSID and password.
        
        Args:
            ssid (str): network name (e.g., "ESP32-D0WDQ6-9774").
            password (str): password to connect.
        """
        self.led.set_mode("not_connected")  # Indicate no clients yet

        self.ap.active(True)  # Enable access point
        self.ap.config(essid=ssid, password=password, authmode=3)  # WPA2-PSK

        # Wait for AP to become active
        while not self.ap.active():
            await asyncio.sleep(1)

        self.led.set_mode("idle")  # Ready to accept connections
        print(f"Access point started: {ssid}")

    def check_client_connected(self):
        """Check whether any clients are connected to the AP.
        
        Returns:
            bool: True if at least one client is connected.
        """
        stations = self.ap.status('stations')  # List of connected clients
        self.client_connected = len(stations) > 0
        return self.client_connected

    def get_ip(self):
        """Get the IP address of the AP.
        
        Returns:
            str: IP address (e.g., "192.168.4.1").
        """
        return self.ap.ifconfig()[0]
    
class WiFiClient:
    def __init__(self, led):
        """Initialize WiFi in Station (Client) mode.
        
        Args:
            led (LEDController): controls the LED (connection status).
        """
        self.led = led
        self.sta = network.WLAN(network.STA_IF)  # Station interface
        self.connected = False  # Connection flag

    async def connect(self, ssid, password):
        """Connect to an external WiFi network.
        
        Args:
            ssid (str): network name (e.g., "LexNET_2.4GHz").
            password (str): password to connect.
        """
        self.led.set_mode("not_connected")  # Indicate not connected

        self.sta.active(True)  # Activate station interface
        self.sta.connect(ssid, password)  # Attempt to connect

        # Wait for connection (~10 seconds timeout)
        while not self.sta.isconnected():
            await asyncio.sleep(1)

        self.connected = True
        self.led.set_mode("connected")  # Indicate successful connection
        print(f"Connected to network: {ssid}")

    def is_connected(self):
        """Check current connection status.
        
        Returns:
            bool: True if connected to a network.
        """
        return self.sta.isconnected()

    def get_ip(self):
        """Get the assigned IP address.
        
        Returns:
            str: IP address (e.g., "192.168.1.100"), or None if not connected.
        """
        return self.sta.ifconfig()[0] if self.sta.isconnected() else None