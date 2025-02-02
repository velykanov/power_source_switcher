#!/usr/bin/env python
import asyncio
import datetime
import enum

try:
    import RPi.GPIO as GPIO
except ImportError:
    # for testing purposes only; tests are not meant to run on raspberry pi
    class GPIO:
        pass

GRID_CONTROL = 23
SECONDARY_CONTROL = 24

TIME_FOR_GRID = datetime.time(23, 1)
TIME_FOR_SECONDARY = datetime.time(6, 59)


class Source(enum.IntEnum):
    GRID = 0
    SECONDARY = 1


class Controller:
    def __init__(self):
        self.source = None
        self.switch_task = None

    async def setup(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GRID_CONTROL, GPIO.OUT)
        GPIO.setup(SECONDARY_CONTROL, GPIO.OUT)

        self.source = Source.SECONDARY

    @property
    async def is_time_to_switch(self) -> bool:
        now = datetime.datetime.now().time()
        is_night = TIME_FOR_GRID <= now or now < TIME_FOR_SECONDARY  # Night: 11 PM to 7 AM
        return (
            (self.source == Source.SECONDARY and is_night) or
            (self.source == Source.GRID and not is_night)
        )

    async def switch_source(self):
        """ Debounced switch: cancels previous task if new request comes in """
        if self.switch_task:
            self.switch_task.cancel()
            self.switch_task = None
            return

        self.switch_task = asyncio.create_task(self._do_switch_source(), name=f'Switch from {self.source.name}')

    async def _do_switch_source(self):
        """ Actual switch operation after debounce delay """
        await asyncio.sleep(5)  # Debounce delay

        self.source = Source.GRID if self.source == Source.SECONDARY else Source.SECONDARY
        GPIO.output(GRID_CONTROL if self.source == Source.SECONDARY else SECONDARY_CONTROL, GPIO.LOW)
        GPIO.output(SECONDARY_CONTROL if self.source == Source.SECONDARY else GRID_CONTROL, GPIO.HIGH)

    async def run(self):
        await self.setup()

        try:
            while True:
                if await self.is_time_to_switch:
                    await self.switch_source()
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            print("Async loop cancelled, cleaning up...")
        finally:
            GPIO.cleanup()


if __name__ == '__main__':
    controller = Controller()
    asyncio.run(controller.run())
