import socket
import uasyncio as asyncio
import json
import network

class Pairing:
    def __init__(self, hostname, ip, led):
        """
        Initialize the pairing handler.
        
        Args:
            hostname (str): Device's own hostname.
            ip (str): Device's own IP address.
            led (LEDController): Object that controls the LED status indicator.
        """
        self.hostname = hostname              # Local device hostname
        self.ip = ip                          # Local device IP address
        self.led = led                        # LED controller for visual feedback
        self.sock = None                      # UDP socket (will be initialized in start())
        self.paired = False                   # Indicates whether pairing has completed

    async def start(self):
        """
        Start the pairing process by opening a UDP socket, enabling broadcast,
        and listening for incoming pairing requests from clients.
        """
        # Create a UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Enable broadcast option so the device can receive broadcast packets
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Make socket non-blocking to allow asynchronous I/O
        self.sock.setblocking(False)

        # Bind socket to port 5000 on all interfaces
        self.sock.bind(('', 5000))

        print("Starting pairing process...")

        # Set LED to indicate that the device is in pairing mode
        self.led.set_mode("pairing")

        # Start listening for incoming pairing requests asynchronously
        asyncio.create_task(self._listen_for_pairing())

    async def _listen_for_pairing(self):
        """
        Listen for incoming UDP messages that indicate a pairing request.
        If a valid message is received, respond and try to complete the pairing process.
        """
        while not self.paired:
            try:
                # Wait for a UDP message with a short timeout
                data, addr = await asyncio.wait_for(
                    self._recvfrom_nonblocking(),
                    timeout=0.1
                )
                # Decode and parse the received JSON message
                message = json.loads(data.decode())

                # Check if the message is a pairing request
                if message.get("type") == "pairing":
                    print(f"Received pairing request from {addr}")
                    await self._respond_to_pairing(message, addr)

            except asyncio.TimeoutError:
                # No data received within timeout period — this is normal
                pass
            except Exception as e:
                # Some unexpected error occurred while receiving
                print(f"Error receiving message: {e}")
                self.led.set_mode("not_connected")

            await asyncio.sleep(0)  # Yield control to the event loop

    async def _recvfrom_nonblocking(self):
        """
        Non-blocking version of socket.recvfrom() to be used with asyncio.
        
        Returns:
            tuple: Received data and sender address.
        """
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)  # Try receiving data
                return data, addr
            except OSError as e:
                if e.errno == 11:  # EAGAIN: no data available right now
                    await asyncio.sleep(0)
                else:
                    raise  # Other error — re-raise

    async def _respond_to_pairing(self, message, addr):
        """
        Respond to a pairing request with a 'hello' message, then wait for a confirmation.
        
        Args:
            message (dict): Incoming pairing request data.
            addr (tuple): Sender's (IP, port) tuple.
        """
        # Extract client information from the request
        client_ip = message["ip"]
        client_hostname = message["hostname"]
        client_mac = message["mac"]

        # Build a response message with device details
        response = {
            "ip": self.ip,
            "type": "hello",
            "hostname": self.hostname,
            "mac": self._format_mac(network.WLAN(network.STA_IF).config('mac'))
        }

        # Send the response multiple times to improve reliability
        for _ in range(5):
            self.sock.sendto(json.dumps(response).encode(), addr)
            print(f"Sent hello response to {addr}")
            await asyncio.sleep(1)  # Delay between responses

        # Wait for confirmation from client that pairing was successful
        if await self._wait_for_paired_confirmation(client_ip):
            print("Pairing successful")
        else:
            print("Pairing failed")

    async def _wait_for_paired_confirmation(self, client_ip):
        """
        Wait for a 'paired' message from the client confirming the pairing.
        
        Args:
            client_ip (str): IP address of the client we're expecting to confirm.
        
        Returns:
            bool: True if pairing confirmation received, False otherwise.
        """
        for _ in range(5):  # Try multiple times in case of packet loss
            try:
                # Wait for incoming message
                data, addr = await asyncio.wait_for(
                    self._recvfrom_nonblocking(),
                    timeout=0.1
                )
                message = json.loads(data.decode())

                # Check if this is the expected pairing confirmation
                if message.get("type") == "paired" and message["ip"] == self.ip:
                    print(f"Client {client_ip} paired successfully")
                    self.paired = True
                    self.led.set_mode("connected")  # Set LED to indicate connection
                    return True

            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"Error waiting for paired confirmation: {e}")

            await asyncio.sleep(0)  # Yield to the event loop

        # If we got here, pairing confirmation failed
        print("Failed to pair with client")
        self.led.set_mode("not_connected")
        return False

    def _format_mac(self, mac_bytes):
        """
        Convert raw MAC bytes into a readable hexadecimal string.
        
        Args:
            mac_bytes (bytes): MAC address in bytes.
        
        Returns:
            str: Formatted MAC address as a lowercase hex string.
        """
        return ''.join("{:02x}".format(b) for b in mac_bytes)

    def close(self):
        """
        Close the socket if it was opened.
        """
        if self.sock:
            self.sock.close()
            self.sock = None