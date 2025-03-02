import uasyncio as asyncio
from machine import Pin

class Elevator:
    def __init__(self):
        """Инициализация лифтов."""
        # Константы
        self.STEPS_PER_FLOOR = 5  # Количество шагов для перемещения между этажами

        # Настройка пинов для внешних кнопок вызова
        self.button_1 = Pin(4, Pin.IN, Pin.PULL_UP)  # Кнопка вызова на 1 этаже
        self.button_2 = Pin(5, Pin.IN, Pin.PULL_UP)  # Кнопка вызова на 2 этаже
        self.button_3 = Pin(12, Pin.IN, Pin.PULL_UP)  # Кнопка вызова на 3 этаже

        # Настройка пинов для внутренних кнопок
        self.inside_button_1 = Pin(13, Pin.IN, Pin.PULL_UP)  # Кнопка "1 этаж"
        self.inside_button_2 = Pin(14, Pin.IN, Pin.PULL_UP)  # Кнопка "2 этаж"
        self.inside_button_3 = Pin(15, Pin.IN, Pin.PULL_UP)  # Кнопка "3 этаж"

        # Настройка пина для кнопки PRG
        self.prg_button = Pin(0, Pin.IN, Pin.PULL_UP)  # Кнопка PRG подключена к GPIO0

        # Настройка пинов для шаговых двигателей
        self.motor_pins = [
            [Pin(16, Pin.OUT), Pin(17, Pin.OUT), Pin(18, Pin.OUT), Pin(19, Pin.OUT)],  # Лифт 1
            [Pin(21, Pin.OUT), Pin(22, Pin.OUT), Pin(23, Pin.OUT), Pin(25, Pin.OUT)],  # Лифт 2
            [Pin(26, Pin.OUT), Pin(27, Pin.OUT), Pin(32, Pin.OUT), Pin(33, Pin.OUT)]  # Лифт 3
        ]

        # Настройка пинов для сдвигового регистра (74HC595)
        self.SER = Pin(25, Pin.OUT)   # Данные (DS)
        self.SRCLK = Pin(26, Pin.OUT) # Тактовый сигнал для сдвига (SHCP)
        self.RCLK = Pin(27, Pin.OUT)  # Тактовый сигнал для защелки (STCP)

        # Настройка пина для светодиода
        self.led = Pin(2, Pin.OUT)

        # Текущие этажи лифтов
        self.current_floors = [1, 1, 1]  # Лифты начинают с 1 этажа

        # Списки для хранения вызовов и запросов
        self.calls = []  # Вызовы с этажей
        self.requests = [None, None, None]  # Запросы для лифтов (None, если лифт свободен)

        # Последовательность шагов для шагового двигателя
        self.step_sequence = [
            [1, 0, 0, 1],
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [0, 1, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 1, 1],
            [0, 0, 0, 1]
        ]

    def shift_out(self, data):
        """Передача данных в сдвиговый регистр."""
        self.RCLK.off()  # Защелкиваем низкий уровень на RCLK
        for i in range(7, -1, -1):
            self.SER.value((data >> i) & 1)  # Устанавливаем значение бита
            self.SRCLK.on()  # Импульс на SRCLK
            self.SRCLK.off()
        self.RCLK.on()  # Защелкиваем данные на выходах

    def update_leds(self, lift_id, state):
        """Управление светодиодами."""
        led_state = 0
        if state:
            led_state = 1 << lift_id  # Включаем соответствующий светодиод
        self.shift_out(led_state)

    async def step_motor(self, motor_pins, direction):
        """Выполнение шага двигателя."""
        if direction == "forward":
            self.step_sequence.reverse()  # Реверсируем последовательность для обратного вращения
        for step in self.step_sequence:
            for i in range(4):
                motor_pins[i].value(step[i])
            await asyncio.sleep_ms(2)  # Асинхронная задержка

    async def move_to_floor(self, lift_id, target_floor):
        """Движение лифта на определенный этаж."""
        steps_needed = abs(target_floor - self.current_floors[lift_id]) * self.STEPS_PER_FLOOR
        direction = "forward" if target_floor > self.current_floors[lift_id] else "backward"
        for _ in range(steps_needed):
            await self.step_motor(self.motor_pins[lift_id], direction)
        self.current_floors[lift_id] = target_floor
        print(f"Лифт {lift_id + 1} на этаже:", target_floor)
        # Включаем светодиод (имитация открытия дверей)
        self.update_leds(lift_id, 1)
        await asyncio.sleep(1)  # Асинхронная задержка
        self.update_leds(lift_id, 0)  # Выключаем светодиод

    async def reset_lifts(self):
        """Сброс состояния лифтов."""
        print("Сброс состояния лифтов...")
        self.calls = []
        self.requests = [None, None, None]
        for lift_id in range(3):
            if self.current_floors[lift_id] != 1:
                print(f"Лифт {lift_id + 1} перемещается на 1 этаж...")
                await self.move_to_floor(lift_id, 1)
        self.current_floors = [1, 1, 1]
        print("Состояние лифтов сброшено, все лифты на 1 этаже.")

    def assign_call(self, call_floor):
        """Распределение вызовов между лифтами."""
        distances = [abs(self.current_floors[i] - call_floor) for i in range(3)]
        for lift_id in range(3):
            if self.requests[lift_id] is None:
                return lift_id
        return distances.index(min(distances))

    async def handle_external_buttons(self):
        """Обработка внешних кнопок."""
        while True:
            if self.button_1.value() == 0 and 1 not in self.calls:
                self.calls.append(1)
            if self.button_2.value() == 0 and 2 not in self.calls:
                self.calls.append(2)
            if self.button_3.value() == 0 and 3 not in self.calls:
                self.calls.append(3)
            await asyncio.sleep(0.1)

    async def handle_lifts(self):
        """Обработка лифтов."""
        while True:
            for lift_id in range(3):
                if self.requests[lift_id] is not None:
                    await self.move_to_floor(lift_id, self.requests[lift_id])
                    print(f"Лифт {lift_id + 1} ожидает выбора этажа...")
                    while True:
                        if self.inside_button_1.value() == 0:
                            self.requests[lift_id] = 1
                            break
                        if self.inside_button_2.value() == 0:
                            self.requests[lift_id] = 2
                            break
                        if self.inside_button_3.value() == 0:
                            self.requests[lift_id] = 3
                            break
                        await asyncio.sleep(0.1)
                    await self.move_to_floor(lift_id, self.requests[lift_id])
                    self.requests[lift_id] = None
            await asyncio.sleep(0.1)

    async def handle_prg_button(self):
        """Обработка кнопки PRG."""
        while True:
            if self.prg_button.value() == 0:
                print("Кнопка PRG нажата")
                await self.reset_lifts()
                await asyncio.sleep(1)
            await asyncio.sleep(0.1)

    async def blink(self):
        """Мигание светодиодом."""
        while True:
            self.led.value(1)
            await asyncio.sleep(1)
            self.led.value(0)
            await asyncio.sleep(1)