import socket
import uasyncio as asyncio
import json
import network
from machine import unique_id

class Pairing:
    def __init__(self, led):
        """
        Initialize the Pairing instance with the given LED controller.
        Args:
            led: LEDController object to update LED states during the pairing process.
        """
        self.led = led  # LED controller to visually indicate pairing progress
        self.sock = None  # Placeholder for the UDP socket used for communication

    async def start(self):
        """
        Start the pairing process by broadcasting a pairing request and awaiting a server response.
        Returns:
            The server's IP address if pairing is successful, or None if it fails.
        """
        # Create a UDP socket for broadcasting messages
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcast mode
        self.sock.setblocking(False)  # Set socket to non-blocking mode

        print("Starting pairing process...")
        self.led.set_mode("pairing")  # Set LED to indicate pairing mode

        # Send a pairing request 5 times with a delay between each attempt
        for i in range(5):
            message = json.dumps({
                "type": "pairing",  # Message type to identify the request
                "ip": self.get_ip(),  # IP address of the device
                "hostname": "esp32-client",  # Hostname for identification
                "mac": self.get_mac()  # Unique MAC address of the device
            })
            print(f"Sent message: {message}")  # Log the message being sent
            self.sock.sendto(message.encode(), ("255.255.255.255", 5000))  # Broadcast the message
            print(f"Sent pairing request {i + 1}/5")  # Log the attempt number
            await asyncio.sleep(1)  # Wait 1 second before sending the next request

        # Wait for a response from the server
        server_ip = await self._wait_for_response()
        if server_ip:
            # If a response is received, send a paired confirmation to the server
            await self._send_paired_confirmation(server_ip)
            return server_ip
        return None  # Return None if no response is received

    async def _wait_for_response(self):
        """
        Wait for a response from the server after sending the pairing requests.
        Returns:
            The server's IP address if a response is received, or None if no response is received.
        """
        for i in range(10):  # Wait for up to 10 seconds
            try:
                # Try to receive data from the socket
                data, addr = self.sock.recvfrom(1024)
                message = json.loads(data.decode())  # Decode the received JSON message
                if message.get("type") == "hello":  # Check if the message type is "hello"
                    print(f"Received hello from {addr}")  # Log the server's address
                    return message["ip"]  # Return the server's IP address
            except Exception as e:
                # Handle any exceptions during the receiving process
                print(f"Error: {e}")
            print(f"Waiting for server response ({i + 1}/10)...")  # Log the waiting status
            await asyncio.sleep(1)  # Wait 1 second before retrying
        return None  # Return None if no response is received after 10 attempts

    async def _send_paired_confirmation(self, server_ip):
        """
        Send a confirmation message to the server indicating that the pairing was successful.
        Args:
            server_ip: The IP address of the server.
        """
        message = json.dumps({
            "type": "paired",  # Message type to identify the confirmation
            "ip": server_ip  # Include the server's IP address
        })
        self.sock.sendto(message.encode(), (server_ip, 5000))  # Send the confirmation message
        print(f"Sent paired confirmation to {server_ip}")  # Log the confirmation sent

    def get_ip(self):
        """
        Get the device's current IP address.
        Returns:
            The IP address as a string.
        """
        return network.WLAN(network.STA_IF).ifconfig()[0]  # Retrieve the IP address from the network interface

    def get_mac(self):
        """
        Get the device's unique MAC address.
        Returns:
            The MAC address as a string of hexadecimal values.
        """
        return "".join("{:02x}".format(b) for b in unique_id())  # Generate MAC address from unique ID