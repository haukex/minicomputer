#!/usr/bin/env python3
from contextlib import contextmanager, closing
from typing import Optional
from RPi import GPIO
import asyncio
import signal
import uinput
import time

@contextmanager
def gpio_session(mode=GPIO.BCM):
    GPIO.setwarnings(True)
    GPIO.setmode(mode)
    try:
        yield GPIO
    finally:
        GPIO.cleanup()


STEP_PIXELS = 3    # mouse movement pixels
INTERVAL_S = 0.02  # mouse movement poll interval (when holding joystick)
BTN_MAP = {
    21: uinput.BTN_LEFT,    # KEY1
    20: uinput.BTN_RIGHT,   # KEY2
    16: uinput.BTN_MIDDLE,  # KEY3
    13: uinput.BTN_LEFT,    # Joystick Press
}
JOY_MAP = {
    6:  (0, -STEP_PIXELS),  # Up
    19: (0,  STEP_PIXELS),  # Down
    5:  (-STEP_PIXELS, 0),  # Left
    26: ( STEP_PIXELS, 0),  # Right
}
ALL_PINS = tuple(BTN_MAP)+tuple(JOY_MAP)
EVENTS = tuple(BTN_MAP.values())+(uinput.REL_X,uinput.REL_Y)


loop = asyncio.new_event_loop()
with closing(loop), gpio_session(), uinput.Device(EVENTS) as device:
    asyncio.set_event_loop(loop)

    # pin directions
    for pin in ALL_PINS:
        GPIO.setup(pin, GPIO.IN, GPIO.PUD_UP)

    # mouse buttons
    async def handle_btn(pin):
        #pressed = not GPIO.input(pin)
        #device.emit(BTN_MAP[pin], 1 if pressed else 0)
        device.emit(BTN_MAP[pin], 0 if GPIO.input(pin) else 1)
    for pin in BTN_MAP:
        # these callbacks will get called in RPi.GPIO's callback thread
        GPIO.add_event_detect(pin, GPIO.BOTH, lambda pin:
            loop.call_soon_threadsafe(asyncio.create_task, handle_btn(pin)) )

    # joystick control
    poll_timer :Optional[asyncio.TimerHandle] = None
    async def handle_joy():
        global poll_timer
        # prevent duplicate events on multiple joystick event edges
        if poll_timer is not None:
            poll_timer.cancel()
            poll_timer = None
        rel_x,rel_y = 0,0
        for pin,(x,y) in JOY_MAP.items():
            if not GPIO.input(pin):
                rel_x += x
                rel_y += y
        if rel_x or rel_y:
            device.emit(uinput.REL_X, rel_x, syn=False)
            device.emit(uinput.REL_Y, rel_y)
            poll_timer = loop.call_later(INTERVAL_S, lambda: asyncio.create_task(handle_joy()))
    for pin in JOY_MAP:
        GPIO.add_event_detect(pin, GPIO.BOTH, lambda _pin:
            loop.call_soon_threadsafe(asyncio.create_task, handle_joy()))

    # main loop
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: loop.stop())
    loop.run_forever()

