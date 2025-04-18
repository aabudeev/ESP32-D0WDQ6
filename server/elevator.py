import uasyncio as asyncio
from typing import Optional, Dict, List, Tuple, Any

class ElevatorManager:
    """
    Manages multiple elevators using a shared motor controller.
    Handles elevator calls, movements, and queue management.
    """

    def __init__(self, motor_controller):
        """
        Initialize the manager with a given motor controller.

        Args:
            motor_controller: An instance of MotorController class controlling motors.
        """
        self.motors = motor_controller
        self.elevators: Dict[int, Dict[str, Any]] = {
            0: {'floor': 1, 'target': None, 'status': 'idle', 'queue': [], 'active': False},
            1: {'floor': 1, 'target': None, 'status': 'idle', 'queue': [], 'active': False},
            2: {'floor': 1, 'target': None, 'status': 'idle', 'queue': [], 'active': False}
        }
        self.call_queue: List[Tuple[int, Optional[int]]] = []  # (floor, preferred_elevator)
        self.lock = asyncio.Lock()  # Protect shared state

    async def call_elevator(self, floor: int, preferred_elevator: Optional[int] = None) -> Dict[str, int]:
        """
        Handle external call to bring an elevator to the requested floor.

        Args:
            floor: The floor requesting the elevator.
            preferred_elevator: Specific elevator ID if preferred.

        Returns:
            Dict with selected elevator ID and target floor.
        """
        print(f"Call received for floor {floor}, preferred elevator: {preferred_elevator}")
        async with self.lock:
            self.call_queue.append((floor, preferred_elevator))

        if preferred_elevator is not None and preferred_elevator in self.elevators:
            if self.elevators[preferred_elevator]['status'] == 'idle':
                return {"elevator": preferred_elevator, "floor": floor}

        elevator_id = await self._select_best_elevator(floor)
        return {"elevator": elevator_id, "floor": floor}

    async def _process_queues(self):
        """
        Continuously processes the global call queue and assigns elevators.
        Should be started as a background task.
        """
        while True:
            async with self.lock:
                if not self.call_queue:
                    await asyncio.sleep(0.1)
                    continue

                floor, preferred = self.call_queue.pop(0)
                elevator_id = await self._select_best_elevator(floor)
                print(f"elevator_id: {elevator_id}")

                if elevator_id is None:
                    self.call_queue.append((floor, preferred))
                    await asyncio.sleep(1)
                    continue

            await self._assign_floor(elevator_id, floor)

    async def _select_best_elevator(self, floor: int) -> Optional[int]:
        """
        Determine which elevator should respond to a call based on current state.

        Priority:
            1. Elevator already on the requested floor and idle.
            2. Nearest idle elevator.
            3. Elevator with the shortest queue.

        Args:
            floor: Floor number to be serviced.

        Returns:
            Elevator ID (int) or None.
        """
        async with self.lock:
            # 1. Check if an elevator is already on the floor and idle
            for elev_id, elev in self.elevators.items():
                if elev['floor'] == floor and elev['status'] == 'idle':
                    return elev_id

            # 2. Find the closest idle elevator
            available = []
            for elev_id, elev in self.elevators.items():
                if elev['status'] == 'idle':
                    distance = abs(elev['floor'] - floor)
                    available.append((elev_id, distance))

            if available:
                return min(available, key=lambda x: x[1])[0]

            # 3. If all are busy, choose one with the smallest queue
            min_queue = min(len(e['queue']) for e in self.elevators.values())
            for elev_id, elev in self.elevators.items():
                if len(elev['queue']) == min_queue:
                    return elev_id

            return 0  # Default fallback

    async def _assign_floor(self, elevator_id: int, floor: int):
        """
        Assign the selected floor to a specific elevator and perform movement.

        Args:
            elevator_id: The ID of the elevator to assign.
            floor: The target floor.
        """
        elev = self.elevators[elevator_id]
        if floor == elev['floor']:
            async with self.lock:
                elev['active'] = True
            return

        elev['target'] = floor
        elev['status'] = 'moving'

        try:
            await self.motors.move_to_floor(elevator_id, floor)
            async with self.lock:
                elev['floor'] = floor
                elev['target'] = None
                elev['status'] = 'idle'
                elev['active'] = True
        except Exception as e:
            async with self.lock:
                elev['status'] = 'error'
                elev['active'] = False

    async def deactivate_elevator(self, elevator_id: int):
        """
        Mark elevator as inactive (e.g., door opened or load in progress).

        Args:
            elevator_id: The ID of the elevator.
        """
        async with self.lock:
            self.elevators[elevator_id]['active'] = False

    async def send_elevator(self, elevator_id: int, floor: int):
        """
        Send a specific elevator to a floor manually.

        Args:
            elevator_id: Elevator index to move.
            floor: Target floor.
        """
        print(f"[ELEVATOR DEBUG] Sending elevator {elevator_id} to floor {floor}")
        if elevator_id not in self.elevators:
            raise ValueError(f"Invalid elevator ID: {elevator_id}")

        self.elevators[elevator_id]['queue'].append(floor)
        await self._process_elevator_queue(elevator_id)

    async def _process_elevator_queue(self, elevator_id: int):
        """
        Process all queued destinations for a specific elevator.

        Args:
            elevator_id: Elevator to process queue for.
        """
        print(f"[QUEUE DEBUG] Processing queue for elevator {elevator_id}")
        while self.elevators[elevator_id]['queue']:
            floor = self.elevators[elevator_id]['queue'].pop(0)
            await self._assign_floor(elevator_id, floor)

    async def reset_all(self):
        """
        Resets all elevators to floor 1 and clears all queues.
        """
        for elev_id in self.elevators:
            self.elevators[elev_id]['queue'] = []
            self.elevators[elev_id]['target'] = None
            self.elevators[elev_id]['status'] = 'idle'
            await self.motors.move_to_floor(elev_id, 1)
            self.elevators[elev_id]['floor'] = 1
            self.elevators[elev_id]['active'] = False