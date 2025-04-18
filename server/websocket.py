import usocket as socket
import uasyncio as asyncio
import ubinascii
import hashlib
import json

WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
WS_OPCODE_TEXT = 0x1  # Text frame opcode for WebSocket

class WebSocketServer:
    def __init__(self, motors, led, wifi_ap, elevator):
        """
        Initialize the WebSocket server.

        Args:
            motors: Motor controller for the elevators.
            led: LED controller for indicating connection status.
            wifi_ap: Access point controller.
            elevator: Elevator controller instance.
        """
        self.motors = motors
        self.led = led
        self.wifi_ap = wifi_ap
        self.elevator = elevator
        self.tasks = {}  # Dictionary to store tasks by ID
        self.client_connected = False

    async def start(self, host: str = "0.0.0.0", port: int = 80):
        """
        Start the WebSocket server.

        Args:
            host: IP address to bind to.
            port: Port to listen on.
        """
        server = await asyncio.start_server(self.handle_client, host, port)
        print(f"WebSocket server started on ws://{host}:{port}")
        await server.wait_closed()

    async def handle_client(self, reader, writer):
        """
        Handle incoming client connections.

        Args:
            reader: StreamReader object.
            writer: StreamWriter object.
        """
        print("Client connected")
        self.client_connected = True
        self.led.set_mode("connected")

        try:
            # Perform WebSocket handshake
            await self.handshake(reader, writer)

            # Continuously receive and process messages
            while True:
                data = await self.receive_frame(reader)
                if not data:
                    break
                print("Received:", data)
                await self.process_message(writer, data)
        except Exception as e:
            print("Client disconnected:", e)
            self.led.set_mode("not_connected")
        finally:
            self.client_connected = False
            self.led.set_mode("connecting")
            writer.close()
            await writer.wait_closed()
            print("Client fully disconnected")

    async def handshake(self, reader, writer):
        """
        Perform WebSocket handshake with client.

        Args:
            reader: StreamReader for reading client request.
            writer: StreamWriter for sending response.
        """
        request_line = await reader.readline()
        headers = {}
        while True:
            line = await reader.readline()
            if line == b"\r\n" or line == b"":
                break
            key, value = line.decode().strip().split(": ", 1)
            headers[key] = value

        if "Sec-WebSocket-Key" not in headers:
            raise ValueError("Invalid WebSocket handshake")

        # Generate accept key for WebSocket handshake
        key = headers["Sec-WebSocket-Key"]
        accept_key = ubinascii.b2a_base64(
            hashlib.sha1((key + WS_MAGIC_STRING).encode()).digest()
        ).strip()

        # Send handshake response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key.decode()}\r\n\r\n"
        )
        writer.write(response.encode())
        await writer.drain()

    async def receive_frame(self, reader) -> str | None:
        """
        Receive and decode a WebSocket frame.

        Args:
            reader: StreamReader to read data from.

        Returns:
            Decoded message string or None if no data.
        """
        header = await reader.read(2)
        if not header:
            return None

        fin = (header[0] & 0x80) >> 7
        opcode = header[0] & 0x0F
        mask = (header[1] & 0x80) >> 7
        length = header[1] & 0x7F

        if length == 126:
            length = int.from_bytes(await reader.read(2), "big")
        elif length == 127:
            length = int.from_bytes(await reader.read(8), "big")

        if mask:
            masking_key = await reader.read(4)

        data = await reader.read(length)
        if mask:
            data = bytes([data[i] ^ masking_key[i % 4] for i in range(len(data))])

        if opcode == WS_OPCODE_TEXT:
            return data.decode()
        return None

    async def send_frame(self, writer, data: str):
        """
        Send a WebSocket text frame to the client.

        Args:
            writer: StreamWriter to write data.
            data: String data to send.
        """
        header = bytearray()
        header.append(0x80 | WS_OPCODE_TEXT)
        if len(data) < 126:
            header.append(len(data))
        elif len(data) < 65536:
            header.append(126)
            header.extend(len(data).to_bytes(2, "big"))
        else:
            header.append(127)
            header.extend(len(data).to_bytes(8, "big"))

        writer.write(header)
        writer.write(data.encode())
        await writer.drain()

    async def process_message(self, writer, message: str):
        """
        Process incoming JSON messages and dispatch to the correct handler.

        Args:
            writer: StreamWriter to respond to client.
            message: JSON-formatted string message.
        """
        try:
            data = json.loads(message)
            if "call" in data:
                await self.handle_call(writer, data["call"])
            elif "task" in data:
                await self.handle_task(writer, data["task"])
            elif "status" in data:
                await self.handle_status(writer, data["status"])
            elif "reset" in data:
                await self.handle_reset(writer)
            else:
                await self.send_frame(writer, json.dumps({"error": "Invalid request"}))
        except Exception as e:
            print("Error processing message:", e)
            await self.send_frame(writer, json.dumps({"error": str(e)}))

    async def handle_call(self, writer, call_data: dict):
        """
        Handle a 'call' request — user pressed elevator button on floor.

        Args:
            writer: StreamWriter to respond to client.
            call_data: Dictionary with 'floor' and optional 'elevator'.
        """
        floor = int(call_data["floor"])
        elevator_id = int(call_data.get("elevator", 0))

        await self.send_frame(writer, json.dumps({
            "response": {
                "type": "call",
                "floor": floor,
                "elevator": elevator_id,
                "status": "processing"
            }
        }))

        result = await self.elevator.call_elevator(floor, elevator_id)

        await self.send_frame(writer, json.dumps({
            "response": {
                "type": "call",
                "floor": floor,
                "elevator": elevator_id,
                "status": "completed"
            }
        }))

        # Assign floor task after call
        asyncio.create_task(
            self.elevator._assign_floor(result["elevator"], floor)
        )

    async def handle_task(self, writer, task_data: dict):
        """
        Handle a 'task' request — direct elevator to a floor.

        Args:
            writer: StreamWriter to respond.
            task_data: Dictionary with 'motor' (elevator) and 'floor'.
        """
        elevator_id = int(task_data.get("motor", 0))
        floor = int(task_data["floor"])

        await self.send_frame(writer, json.dumps({
            "response": {
                "type": "task",
                "elevator": elevator_id,
                "floor": floor,
                "status": "processing"
            }
        }))

        await self.elevator.send_elevator(elevator_id, floor)

        await self.send_frame(writer, json.dumps({
            "response": {
                "type": "task",
                "elevator": elevator_id,
                "floor": floor,
                "status": "completed"
            }
        }))

    async def handle_status(self, writer, status_data: dict):
        """
        Handle a 'status' request — check the state of a task.

        Args:
            writer: StreamWriter to respond.
            status_data: Dictionary with 'task_id'.
        """
        task_id = status_data["task_id"]
        if task_id in self.tasks:
            task = self.tasks[task_id]
            response = {
                "response": {
                    "task_id": task_id, 
                    "motor": task["motor"], 
                    "floor": task["floor"], 
                    "action": task["action"], 
                    "status": task["status"]
                }
            }
        else:
            response = {"response": {"task_id": task_id, "status": "not_found"}}
        await self.send_frame(writer, json.dumps(response))

    async def handle_reset(self, writer):
        """
        Handle a 'reset' request — reset all elevators to base state.

        Args:
            writer: StreamWriter to respond.
        """
        await self.send_frame(writer, json.dumps({
            "response": {
                "type": "reset",
                "elevator": 6,
                "floor": 1,
                "status": "processing"
            }
        }))

        await self.elevator.reset_all()

        await self.send_frame(writer, json.dumps({
            "response": {
                "type": "reset",
                "elevator": 6,
                "floor": 1,
                "status": "completed"
            }
        }))