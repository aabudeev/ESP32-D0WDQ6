import network
import uasyncio as asyncio
import utime

class WiFiClient:
    def __init__(self, led):
        """
        Initialize the WiFiClient instance with the given LED controller.
        Args:
            led: LEDController object to update LED states based on connectivity.
        """
        self.led = led  # The LED controller to indicate connection status
        self.sta = network.WLAN(network.STA_IF)  # Initialize the STA (Station) interface for Wi-Fi
        self.connected = False  # Connection status flag

    async def scan_networks(self):
        """
        Scan for available Wi-Fi networks and return a list of SSID names.
        Returns:
            A list of SSIDs of the available networks.
        """
        self.sta.active(True)  # Activate the Wi-Fi interface
        networks = self.sta.scan()  # Scan for networks
        ssids = [network[0].decode() for network in networks]  # Extract SSID names
        print(f"Available networks: {ssids}")  # Log the available networks
        return ssids

    async def connect(self, ssid, password):
        """
        Connect to a Wi-Fi network using the provided SSID and password.
        Args:
            ssid: The name of the Wi-Fi network to connect to.
            password: The password for the Wi-Fi network.
        Returns:
            True if the connection is successful, False otherwise.
        """
        self.sta.active(True)  # Activate the Wi-Fi interface
        self.sta.connect(ssid, password)  # Start the connection process

        # Connection timeout in seconds
        timeout = 10
        start_time = utime.ticks_ms()  # Get the current time in milliseconds
        while not self.sta.isconnected():  # Wait until the connection is established
            if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout * 1000:
                # Exit if the connection takes longer than the timeout period
                print(f"Timeout connecting to {ssid}")
                return False
            await asyncio.sleep(1)  # Wait for 1 second before retrying

        self.connected = True  # Update the connection status flag
        print(f"Connected to {ssid}")  # Log successful connection
        return True

    def is_connected(self):
        """
        Check if the device is currently connected to a Wi-Fi network.
        Returns:
            True if connected, False otherwise.
        """
        return self.sta.isconnected()

    def get_ip(self):
        """
        Get the IP address of the device.
        Returns:
            The IP address as a string.
        """
        return self.sta.ifconfig()[0]  # Return the IP address from the interface configuration

    async def connect_to_server(self, guest_wifi, guest_ssid, guest_password, ap_ssid, ap_password, server_mac_suffix):
        """
        Connect to either a guest network or a server access point (AP) based on the configuration.
        This function keeps retrying until a connection is established.

        Args:
            guest_wifi: Boolean, whether to prioritize connecting to a guest network.
            guest_ssid: The SSID of the guest network.
            guest_password: The password for the guest network.
            ap_ssid: The base SSID of the server AP.
            ap_password: The password for the server AP.
            server_mac_suffix: The unique suffix of the server's MAC address.

        Returns:
            True if the connection is successful.
        """
        while True:
            try:
                # Scan for available networks
                ssids = await self.scan_networks()

                if guest_wifi:  # If guest Wi-Fi is prioritized
                    if guest_ssid in ssids:  # Check if the guest network is available
                        print(f"Connecting to guest network: {guest_ssid}")
                        if await self.connect(guest_ssid, guest_password):
                            return True  # Successfully connected to the guest network
                    else:
                        print(f"Guest network {guest_ssid} not found")
                else:
                    # Construct the full SSID of the server's AP using its MAC address suffix
                    server_ssid = f"{ap_ssid}-{server_mac_suffix}"
                    if server_ssid in ssids:  # Check if the server AP is available
                        print(f"Connecting to server AP: {server_ssid}")
                        if await self.connect(server_ssid, ap_password):
                            return True  # Successfully connected to the server AP
                    else:
                        print(f"Server AP {server_ssid} not found")

                # If no network is connected, set LED to indicate "not connected" and retry
                self.led.set_mode("not_connected")
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)  # Wait 5 seconds before retrying
            except Exception as e:
                # Handle any exceptions during the connection process
                print(f"Error during Wi-Fi connection: {e}")
                self.led.set_mode("not_connected")  # Set LED to indicate "not connected"
                await asyncio.sleep(5)  # Wait 5 seconds before retrying