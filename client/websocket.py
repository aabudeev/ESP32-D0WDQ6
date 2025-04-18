import usocket as socket
import uasyncio as asyncio
import json
import time

class WebSocketClient:
    def __init__(self, server_ip, led, buttons, buzzer, ext_leds):
        """
        Initialize the WebSocketClient instance.
        This class manages the WebSocket connection with the server, processes incoming messages, 
        and sends various commands or updates back to the server.
        
        Args:
            server_ip (str): The IP address of the WebSocket server to connect to.
            led (LEDController): LED controller used to update LED states based on connection status.
            buttons (Buttons): Button controller to handle button inputs and events.
            buzzer (Buzzer): Buzzer controller for audio feedback in response to events.
            ext_leds (ExtendedLEDs): Controller for managing additional LEDs (call and panel LEDs).
        """
        self.server_ip = server_ip  # IP address of the WebSocket server
        self.led = led  # LEDController instance to provide visual feedback
        self.buttons = buttons  # Instance to manage button events
        self.buzzer = buzzer  # Buzzer instance for sound signals
        self.ext_leds = ext_leds  # ExtendedLEDs instance for managing multiple LEDs
        self.connected = False  # Boolean flag indicating the WebSocket connection status
        self.writer = None  # StreamWriter instance for sending messages to the server
        self.task = 0  # Identifier for the current task being executed
        self.active_timer = None  # Timer for monitoring active tasks
        self.active_elevators = {}  # Dictionary to track active elevators and their tasks
        self._active_tasks_lock = asyncio.Lock()  # Async lock to ensure thread-safe task management

    async def start(self):
        """
        Starts the WebSocket client. This method attempts to establish a connection to the 
        WebSocket server, perform the handshake, and then listens for and processes incoming messages.

        If the connection fails, it retries after a delay of 5 seconds.
        """
        self.led.set_mode("connecting")  # Set the LED to indicate the connection process
        while True:  # Infinite loop to attempt reconnection in case of failure
            try:
                print(f"Connecting to WebSocket at {self.server_ip}...")
                # Establish a TCP connection to the server on port 80
                reader, writer = await asyncio.open_connection(self.server_ip, 80)
                self.writer = writer  # Save the writer instance for sending messages
                print("WebSocket connection established, performing handshake...")
                
                # Perform the WebSocket handshake to establish a full duplex connection
                await self.handshake(reader, writer)
                self.connected = True  # Mark the connection as successful
                self.led.set_mode("connected")  # Update LED to indicate a successful connection
                print("Connected to WebSocket")
                
                # Continuously read and process incoming messages from the server
                while True:
                    data = await self.receive_frame(reader)
                    if not data:  # Break the loop if no data is received
                        break
                    await self.process_message(data)  # Process the received message

            # Handle connection errors and retry after a delay
            except Exception as e:
                print(f"WebSocket connection failed: {e}")
                self.led.set_mode("not_connected")  # Update LED to indicate disconnection
                await asyncio.sleep(5)  # Wait 5 seconds before retrying

    async def handshake(self, reader, writer):
        """
        Perform the WebSocket handshake with the server. This is necessary to upgrade the 
        TCP connection to a WebSocket connection.

        Args:
            reader (StreamReader): StreamReader for reading server responses.
            writer (StreamWriter): StreamWriter for sending handshake request to the server.

        Raises:
            ValueError: If the server does not respond with a "101 Switching Protocols" status.
        """
        # Format the WebSocket handshake request
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: {}\r\n"  # Specify the server address in the Host header
            "Upgrade: websocket\r\n"  # Indicate the intention to upgrade to WebSocket
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"  # Required key for WebSocket handshake
            "Sec-WebSocket-Version: 13\r\n\r\n"  # Specify WebSocket protocol version
        ).format(self.server_ip)
        writer.write(request.encode())  # Send the handshake request
        await writer.drain()  # Ensure the request is fully sent to the server

        # Read the server's response
        response = await reader.read(1024)
        if b"101 Switching Protocols" not in response:
            # If the response does not include the expected status, raise an error
            raise ValueError("WebSocket handshake failed")

    async def receive_frame(self, reader):
        """
        Receive a WebSocket frame from the server. This method decodes the frame header, 
        extracts the payload, and processes masking if applicable.

        Args:
            reader (StreamReader): StreamReader for reading data from the server.

        Returns:
            str: Decoded message payload if the frame is a text frame, None otherwise.
        """
        header = await reader.read(2)  # Read the first two bytes of the frame header
        if not header:  # Return None if no data is received
            return None

        # Extract frame metadata from the header
        fin = (header[0] & 0x80) >> 7  # Final frame flag
        opcode = header[0] & 0x0F  # Opcode indicating the frame type (e.g., text, binary)
        mask = (header[1] & 0x80) >> 7  # Mask flag
        length = header[1] & 0x7F  # Payload length (7 bits)

        # Handle extended payload lengths (126 or 127 bytes)
        if length == 126:
            length = int.from_bytes(await reader.read(2), "big")  # Read 16-bit length
        elif length == 127:
            length = int.from_bytes(await reader.read(8), "big")  # Read 64-bit length

        # Read the masking key if the mask flag is set
        if mask:
            masking_key = await reader.read(4)

        # Read the payload data
        data = await reader.read(length)
        if mask:
            # Apply the masking key to decode the payload
            data = bytes([data[i] ^ masking_key[i % 4] for i in range(len(data))])

        # If the frame is a text frame (opcode 0x1), decode and return the payload
        if opcode == 0x1:
            return data.decode()
        return None  # Return None for non-text frames

    async def send_frame(self, writer, data):
        """
        Send a WebSocket frame to the server. This method constructs the frame header, 
        appends the payload, and ensures the frame is sent.

        Args:
            writer (StreamWriter): StreamWriter for sending data to the server.
            data (str): The message to send as a WebSocket frame.
        """
        header = bytearray()  # Initialize the frame header
        header.append(0x80 | 0x1)  # Final frame flag and opcode for text frame
        if len(data) < 126:
            header.append(len(data))  # Small payload length
        elif len(data) < 65536:
            header.append(126)  # Extended payload length (16-bit)
            header.extend(len(data).to_bytes(2, "big"))
        else:
            header.append(127)  # Extended payload length (64-bit)
            header.extend(len(data).to_bytes(8, "big"))

        writer.write(header)  # Write the frame header
        writer.write(data.encode())  # Write the payload
        await writer.drain()  # Flush the data to the server to ensure it's sent

    async def _reset_active_elevator(self, elevator_id):
        """
        Deactivate the elevator's active status after a delay.
        This is used to reset the elevator status once its operation is completed or the timer expires.

        Args:
            elevator_id (int): The unique identifier for the elevator to reset.
        """
        try:
            await asyncio.sleep(3)  # Wait for 3 seconds before deactivating
            async with self._active_tasks_lock:  # Acquire the lock to ensure thread-safe access
                if elevator_id in self.active_elevators:
                    del self.active_elevators[elevator_id]  # Remove the elevator from the active list
            print(f"Elevator {elevator_id} deactivated")  # Log the deactivation
        except asyncio.CancelledError:
            # Handle the case where the task is cancelled before completion
            print(f"Elevator {elevator_id} activity was cancelled")

    async def process_message(self, message):
        """
        Process an incoming message from the server.
        Messages can include updates about elevator calls, task completions, or other events.

        Args:
            message (str): The message received from the WebSocket server, in JSON format.
        """
        try:
            data = json.loads(message)  # Parse the JSON message
            print(f"Message from server: {data}")  # Log the received message

            if data.get("response"):  # Check if the message contains a response field
                resp = data["response"]

                if resp["type"] == "call":  # Handle elevator call-related messages
                    if resp.get("status") == "processing":
                        floor = resp["floor"]  # Extract the floor number
                        self.current_call_led_task = asyncio.create_task(
                            self._hold_led(floor, led_type="call")  # Start holding the call LED for the floor
                        )
                    elif resp.get("status") == "completed":
                        floor = resp["floor"]  # Extract the floor number
                        elevator_id = resp.get("elevator", 0)  # Extract the elevator ID (default to 0)

                        # Cancel any ongoing LED hold task for the floor
                        if hasattr(self, 'current_call_led_task'):
                            self.current_call_led_task.cancel()

                        # Blink the call LED and trigger the buzzer for elevator arrival
                        asyncio.create_task(self.ext_leds.blink_call_led(floor))
                        asyncio.create_task(self.buzzer.elevator_signal("arrival"))

                        # Manage the active elevator status
                        async with self._active_tasks_lock:
                            if elevator_id in self.active_elevators:
                                self.active_elevators[elevator_id].cancel()  # Cancel any existing task for the elevator

                            # Start a new task to reset the elevator after a delay
                            self.active_elevators[elevator_id] = asyncio.create_task(
                                self._reset_active_elevator(elevator_id)
                            )
                            print(f"Elevator {elevator_id} activated for floor {floor}")

                elif resp["type"] == "task":  # Handle task-related messages
                    if resp.get("status") == "processing":
                        floor = resp["floor"]  # Extract the floor number
                        self.current_task_led_task = asyncio.create_task(
                            self._hold_led(floor, led_type="panel")  # Start holding the panel LED for the floor
                        )
                    elif resp.get("status") == "completed":
                        floor = resp["floor"]  # Extract the floor number

                        # Cancel any ongoing LED hold task for the floor
                        if hasattr(self, 'current_task_led_task'):
                            self.current_task_led_task.cancel()
                            try:
                                await self.current_task_led_task  # Wait for the task to complete
                            except asyncio.CancelledError:
                                # Handle task cancellation gracefully
                                pass

                        # Blink the panel LED and trigger a melody on the buzzer
                        asyncio.create_task(self.ext_leds.blink_panel_led(floor))
                        asyncio.create_task(self.buzzer.melody())

        except Exception as e:
            # Log any errors encountered while processing the message
            print(f"Error processing message: {e}")

    async def _hold_led(self, floor, led_type="call"):
        """
        Keep the LED on for a specific floor and type until the task is completed or cancelled.

        Args:
            floor (int): The floor number (1-3).
            led_type (str): The type of LED to control ("call" for call LEDs, "panel" for panel LEDs).
        """
        try:
            if 1 <= floor <= 3:  # Ensure the floor number is within valid range
                led_index = floor - 1  # Calculate the LED index (0-based)
                if led_type == "call":
                    self.ext_leds.call_leds[led_index].on()  # Turn on the call LED for the floor
                else:
                    self.ext_leds.panel_leds[led_index].on()  # Turn on the panel LED for the floor

                while True:
                    await asyncio.sleep(1)  # Keep the LED on indefinitely until cancelled

        except asyncio.CancelledError:
            # Handle task cancellation by turning off the LED
            if 1 <= floor <= 3:  # Ensure the floor number is valid
                led_index = floor - 1
                if led_type == "call":
                    self.ext_leds.call_leds[led_index].off()  # Turn off the call LED
                else:
                    self.ext_leds.panel_leds[led_index].off()  # Turn off the panel LED
        except Exception as e:
            # Log any errors encountered while holding the LED
            print(f"LED hold error: {e}")

    async def send_call(self, floor, elevator=0):
        """
        Send a call request to the server for a specific floor and elevator.

        Args:
            floor (int): The floor number to call the elevator to.
            elevator (int): The elevator ID (default is 0).
        """
        message = json.dumps({
            "call": {
                "floor": floor,  # Floor number
                "elevator": elevator  # Elevator ID
            }
        })
        await self.send_frame(self.writer, message)  # Send the call request to the server

    async def send_task(self, floor, motor):
        """
        Send a task request to the server to move the elevator to a specific floor.

        Args:
            floor (int): The floor number to move the elevator to.
            motor (str): The motor type or direction (e.g., "up", "down").
        """
        print(f"[CLIENT DEBUG] Sending task: motor={motor}, floor={floor}")  # Debug log for the task
        self.task = hash((floor, motor, time.ticks_ms())) % 1000  # Generate a unique task ID
        message = json.dumps({
            "task": {
                "id": self.task,  # Unique task ID
                "motor": motor,  # Motor type or direction
                "floor": floor,  # Floor number
                "action": "move"  # Action type
            }
        })
        await self.send_frame(self.writer, message)  # Send the task request to the server

    async def send_status(self):
        """
        Send the current task status to the server.
        This includes the ID of the last task initiated by the client.
        """
        message = json.dumps({
            "status": {
                "task_id": self.task  # ID of the current task
            }
        })
        await self.send_frame(self.writer, message)  # Send the status update to the server

    async def send_reset(self):
        """
        Send a reset command to the server to clear any ongoing tasks or states.
        This is typically used for error recovery or reinitialization.
        """
        message = json.dumps({"reset": {}})  # Create a reset command message
        await self.send_frame(self.writer, message)  # Send the reset command to the server