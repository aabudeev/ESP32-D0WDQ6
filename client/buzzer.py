from machine import Pin, PWM
import uasyncio as asyncio

class Buzzer:
    """
    This class manages a PWM-based buzzer to produce sounds, tones, and melodies.
    It provides methods for playing individual tones, predefined melodies, and sound signals (e.g., elevator arrival).
    """
    def __init__(self, pin):
        """
        Initialize the Buzzer instance.

        Args:
            pin (int): GPIO pin number to which the buzzer is connected.
        """
        self.pin = pin  # GPIO pin for the buzzer
        self.pwm = None  # PWM object for controlling the buzzer
        self.volume = 512  # Default volume level (50% of the maximum duty cycle)
        self.active = False  # Flag to indicate if the buzzer is currently active
        self._init_pwm()  # Initialize the PWM for the buzzer

    def _init_pwm(self):
        """
        Initialize or reinitialize the PWM object for the buzzer.
        Ensures that the PWM is properly configured and the buzzer is off initially.
        """
        if self.pwm is not None:
            self.pwm.deinit()  # Deinitialize any existing PWM instance
        self.pwm = PWM(Pin(self.pin, Pin.OUT, value=0))  # Create a new PWM instance
        self.pwm.duty(0)  # Set initial duty cycle to 0 (buzzer off)
        self.pwm.freq(1000)  # Set default frequency to 1000 Hz
        self.active = False  # Mark the buzzer as inactive

    async def _ensure_cleanup(self):
        """
        Ensure the buzzer is turned off and the PWM is reset.
        This is used to clean up the buzzer state after playing any sound.
        """
        if self.pwm is not None:
            self.pwm.duty(0)  # Turn off the buzzer
            await asyncio.sleep_ms(20)  # Short delay to ensure the state is stable
        self.active = False  # Mark the buzzer as inactive

    async def play_tone(self, frequency, duration_ms):
        """
        Play a single tone at the specified frequency and duration.

        Args:
            frequency (float): Frequency of the tone in Hz. Use 0 for silence.
            duration_ms (int): Duration of the tone in milliseconds.
        """
        if frequency == 0:  # Play silence
            self.pwm.duty(0)  # Turn off the buzzer
            await asyncio.sleep_ms(duration_ms)  # Wait for the specified duration
        else:
            self.pwm.freq(int(frequency))  # Set the frequency
            self.pwm.duty(512)  # Set duty cycle to 50% to produce sound
            await asyncio.sleep_ms(duration_ms)  # Wait for the duration of the tone
            self.pwm.duty(0)  # Turn off the buzzer
            await asyncio.sleep_ms(50)  # Short delay before ending the tone

    async def melody(self):
        """
        Play a predefined melody (Seven Nation Army intro).
        This melody is composed of multiple notes with specific frequencies and durations.
        """
        # Define frequencies for musical notes
        E4 = 329.63
        G4 = 392.00
        D4 = 293.66
        C4 = 261.63
        B3 = 246.94

        # Define the melody as a sequence of (frequency, duration) tuples
        melody_notes = [
            (E4, 200), (0, 400), (E4, 100), (0, 100), (G4, 100), (0, 200), (E4, 100),
            (0, 200), (D4, 100), (0, 100), (C4, 200), (0, 400), (B3, 400), (0, 400)
        ]

        # Play each note in the melody
        for note in melody_notes:
            frequency, duration = note
            await self.play_tone(frequency, duration)

        self.pwm.duty(0)  # Ensure the buzzer is turned off after the melody

    async def _play_advanced(self, freq, duration_ms, ramp_ms=30):
        """
        Play a tone with a ramp-up and ramp-down effect for smoother transitions.

        Args:
            freq (int): Frequency of the tone in Hz.
            duration_ms (int): Total duration of the tone in milliseconds.
            ramp_ms (int): Duration of the ramp-up and ramp-down in milliseconds.
        """
        await self._ensure_cleanup()  # Ensure the buzzer is clean before starting
        self.active = True  # Mark the buzzer as active

        if freq == 0:  # Handle silence
            await asyncio.sleep_ms(duration_ms)
            return

        self.pwm.freq(int(freq))  # Set the frequency of the tone

        # Ramp-up phase
        steps = max(1, ramp_ms)  # Number of ramp steps
        for i in range(steps):
            self.pwm.duty(int(self.volume * (i / steps)))  # Gradually increase volume
            await asyncio.sleep_ms(1)  # Short delay between steps

        # Sustain phase
        sustain_ms = max(0, duration_ms - 2 * ramp_ms)  # Duration of the constant tone
        await asyncio.sleep_ms(sustain_ms)

        # Ramp-down phase
        for i in range(steps, 0, -1):
            self.pwm.duty(int(self.volume * (i / steps)))  # Gradually decrease volume
            await asyncio.sleep_ms(1)

        await self._ensure_cleanup()  # Clean up after playing the tone

    async def elevator_signal(self, signal_type="arrival"):
        """
        Play predefined sound signals for elevator events (e.g., arrival, departure).

        Args:
            signal_type (str): The type of signal to play. Options are:
                - "arrival": Signal for elevator arrival.
                - "departure": Signal for elevator departure.
                - "button": Button press confirmation signal.
                - "error": Error signal.
        """
        # Define signal patterns as sequences of (frequency, duration) tuples
        signals = {
            "arrival": [(784, 150), (0, 50), (1047, 300)],
            "departure": [(659, 100), (0, 50), (784, 150), (0, 50), (659, 300)],
            "button": [(523, 80)],
            "error": [(392, 100), (0, 100), (392, 100), (0, 100), (392, 100)]
        }

        await self._ensure_cleanup()  # Ensure the buzzer is clean before starting
        self.active = True  # Mark the buzzer as active

        # Play the sequence of tones for the selected signal type
        for freq, duration in signals.get(signal_type, []):
            await self._play_advanced(freq, duration)

        await self._ensure_cleanup()  # Clean up after playing the signal

    async def set_volume(self, volume):
        """
        Adjust the volume of the buzzer dynamically.

        Args:
            volume (int): Volume level (0-100). Values outside this range are clamped.
        """
        # Convert volume from percentage (0-100) to the PWM duty cycle range (0-1023)
        self.volume = int(min(max(volume, 0), 100) * 10.23)
        if self.active and self.pwm is not None:
            self.pwm.duty(self.volume)  # Update the duty cycle if the buzzer is active

    def deinit(self):
        """
        Deinitialize the PWM and clean up the buzzer state.
        This should be called when the buzzer is no longer needed.
        """
        if self.pwm is not None:
            self.pwm.duty(0)  # Turn off the buzzer
            self.pwm.deinit()  # Deinitialize the PWM instance
            self.pwm = None  # Remove the PWM reference
        self.active = False  # Mark the buzzer as inactive