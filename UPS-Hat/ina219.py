#!/usr/bin/env python3
from pathlib import Path
from more_itertools import one  # sudo apt install python3-more-itertools

hwmon = one(Path('/sys/bus/i2c/devices/1-0043/hwmon').glob('hwmon*'))

bus_mv = int((hwmon/'in1_input').read_text(encoding='ASCII').strip())
curr_ma = int((hwmon/'curr1_input').read_text(encoding='ASCII').strip())

# Same formula as Waveshare's `INA219.py`
percent = (bus_mv/1000 - 3)/1.2*100

status = f"charging {curr_ma:d}mA" if curr_ma>0 else f"discharging {-curr_ma:d}mA" if curr_ma<0 else 'idle'

print(f"{bus_mv/1000:.3f}V {percent:.1f}% {status}")
