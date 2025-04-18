from machine import Pin
import uasyncio as asyncio
import time
from typing import List, Tuple, Dict

class MotorController:
    """
    A controller for managing stepper motors that simulate elevator movement between floors.
    """

    def __init__(self, motor_pins: List[Tuple[int, int, int]]):
        """
        Initialize the motor controller with pin configurations for each motor.

        Args:
            motor_pins: A list of tuples, each containing (step_pin, dir_pin, enable_pin) for one motor.
        """
        self.motors: List[Dict[str, Pin]] = []

        for step_pin, dir_pin, enable_pin in motor_pins:
            self.motors.append({
                "step": Pin(step_pin, Pin.OUT),
                "dir": Pin(dir_pin, Pin.OUT),
                "enable": Pin(enable_pin, Pin.OUT)
            })

        # Disable all motors initially
        for motor in self.motors:
            motor["enable"].off()

        self.moving_status: List[bool] = [False] * len(motor_pins)  # Track movement status of each motor
        self.stop_request: List[bool] = [False] * len(motor_pins)   # Track stop requests
        self.current_steps: List[int] = [0] * len(motor_pins)       # Track steps taken
        self.current_floor: List[int] = [1] * len(motor_pins)       # Current floor of each motor

        # Constants
        self.STEPS_PER_FLOOR: int = 550        # Number of steps for floor
        self.MIN_STEP_DELAY_US: int = 500      # Fastest delay (max speed)
        self.ACCELERATION_STEPS: int = 50      # Number of steps for acceleration/deceleration
        self.MAX_STEP_DELAY_US: int = 2000     # Slowest delay (start/end speed)

    async def enable_motor(self, motor_index: int, enable: bool = True):
        """
        Enable or disable a specific motor.

        Args:
            motor_index: Index of the motor.
            enable: True to enable, False to disable.
        """
        self.motors[motor_index]["enable"].value(not enable)

    async def step_motor(self, motor_index: int, direction: int):
        """
        Perform a single step in a given direction.

        Args:
            motor_index: Index of the motor.
            direction: 0 or 1 indicating movement direction.
        """
        motor = self.motors[motor_index]
        motor["dir"].value(direction)
        motor["step"].on()
        await self.delay_us(self.MIN_STEP_DELAY_US)
        motor["step"].off()

    async def delay_us(self, us: int):
        """
        Delay for a specified number of microseconds.

        Args:
            us: Number of microseconds to wait.
        """
        if us <= 0:
            return
        elif us >= 1000:
            await asyncio.sleep_ms(us // 1000)
        else:
            start = time.ticks_us()
            while time.ticks_diff(time.ticks_us(), start) < us:
                await asyncio.sleep_ms(0)  # Yield control to the event loop

    async def rotate_motor(self, motor_index: int, steps: int, direction: int):
        """
        Rotate a motor a given number of steps in a specified direction, with acceleration.

        Args:
            motor_index: Index of the motor to rotate.
            steps: Number of steps to take.
            direction: Direction to move the motor (0 or 1).
        """
        if motor_index >= len(self.motors):
            raise ValueError("Invalid motor index")
        if steps == 0:
            return

        self.moving_status[motor_index] = True
        await self.enable_motor(motor_index, True)

        try:
            self.motors[motor_index]["dir"].value(direction)

            def calculate_delay(step: int) -> int:
                """
                Calculate dynamic delay for acceleration and deceleration.

                Args:
                    step: Current step index.

                Returns:
                    Delay in microseconds.
                """
                if step < self.ACCELERATION_STEPS:
                    # Accelerate
                    delay = self.MAX_STEP_DELAY_US - (
                        (self.MAX_STEP_DELAY_US - self.MIN_STEP_DELAY_US) * step / self.ACCELERATION_STEPS
                    )
                elif step > steps - self.ACCELERATION_STEPS:
                    # Decelerate
                    delay = self.MIN_STEP_DELAY_US + (
                        (self.MAX_STEP_DELAY_US - self.MIN_STEP_DELAY_US) * (step - (steps - self.ACCELERATION_STEPS)) / self.ACCELERATION_STEPS
                    )
                else:
                    # Constant speed
                    delay = self.MIN_STEP_DELAY_US
                return int(delay)

            for current_step in range(steps):
                if self.stop_request[motor_index]:
                    break  # Stop request received, exit loop early

                self.motors[motor_index]["step"].on()
                await self.delay_us(self.MIN_STEP_DELAY_US)
                self.motors[motor_index]["step"].off()

                delay = calculate_delay(current_step)
                await self.delay_us(delay)

        finally:
            self.moving_status[motor_index] = False
            await self.enable_motor(motor_index, True)

    def is_moving(self, motor_index: int) -> bool:
        """
        Check if a motor is currently moving.

        Args:
            motor_index: Index of the motor.

        Returns:
            True if moving, False otherwise.
        """
        return self.moving_status[motor_index]

    async def stop_motor(self, motor_index: int):
        """
        Request a motor to stop and wait for it to stop.

        Args:
            motor_index: Index of the motor.
        """
        self.stop_request[motor_index] = True
        while self.moving_status[motor_index]:
            await asyncio.sleep_ms(10)
        self.stop_request[motor_index] = False

    async def move_to_floor(self, motor_index: int, target_floor: int):
        """
        Move a motor to the specified floor.

        Args:
            motor_index: Index of the motor.
            target_floor: Target floor number.
        """
        print(f"[MOTOR DEBUG] Starting move: motor={motor_index}, from={self.current_floor[motor_index]}, to={target_floor}")
        
        if motor_index >= len(self.motors):
            raise ValueError(f"Invalid motor index: {motor_index}")
        if target_floor < 1 or target_floor > 3:
            raise ValueError(f"Invalid floor number: {target_floor}")
        if self.current_floor[motor_index] == target_floor:
            print(f"[MOTOR DEBUG] Motor {motor_index} already on floor {target_floor}")
            return

        floor_diff = target_floor - self.current_floor[motor_index]
        steps = abs(floor_diff) * self.STEPS_PER_FLOOR
        direction = 0 if floor_diff > 0 else 1

        await self.rotate_motor(motor_index, steps, direction)
        self.current_floor[motor_index] = target_floor

    async def reset_all(self):
        """
        Move all motors to floor 1 (reset position).
        """
        for i in range(len(self.motors)):
            if self.current_floor[i] != 1:
                await self.move_to_floor(i, 1)