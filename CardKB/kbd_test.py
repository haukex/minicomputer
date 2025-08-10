#!/usr/bin/env python3
# https://docs.m5stack.com/en/unit/cardkb
import time
import smbus  # sudo apt install python3-smbus

bus = smbus.SMBus(1)  # bus nr 1
while True:
    try:
        key = bus.read_byte(0x5F)  # address 0x5F
        if key:
            print(f"{key:02x}")
        time.sleep(0.100)
    except KeyboardInterrupt:
        break
bus.close()

