Mini-Computer with Raspberry Pi Zero
====================================

Basic Idea:
- Raspberry Pi Zero 2 W
- small mouse and keyboard
- small display
- battery (optional)
- camera (optional)

Current Hardware as based on
[Waveshare Raspberry Pi Zero WH Package F (with UPS Module and 1.3inch LCD Display)](https://www.waveshare.com/raspberry-pi-zero-wh-package-f.htm)
- [Raspberry Pi Zero 2 WH](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) or
  [Raspberry Pi Zero WH](https://www.raspberrypi.com/products/raspberry-pi-zero-w/)
- [Waveshare Uninterruptible Power Supply Hat](https://www.waveshare.com/UPS-HAT-C.htm)
- [Waveshare 1.3" 240x240 IPS LCD display Hat](https://www.waveshare.com/1.3inch-LCD-HAT.htm)
  - includes joystick mouse
- [M5Stack CardKB 1.1](https://docs.m5stack.com/en/unit/cardkb_1.1)


Base Installation
-----------------

<https://github.com/haukex/raspinotes/blob/52bde512/BaseInstall.md>

- For the `fbcp-ili9341` driver below, *must* use 32-bit OS *before* Bookworm, I used:
  "Raspberry Pi OS (Legacy) with desktop, Release date: July 4th 2024, System: 32-bit, Debian version: 11 (bullseye)"
- Set up the second partition (half of the 64GB), but didn't enable overlay filesystem or move the mail directories to `/data` (yet)
- For some reason, after first boot, it didn't get the date/time via NTP; either:
  - use `sudo ntpdate TIMESERVER` (may need the server from the local net)
  - or, to transfer the time from a remote machine:
    `ssh RPI_HOST_IP sudo date --set="$(date -uIs)"` (where `-Is` specifies second accuracy, is not short for `--set`)
- For this repo:
  - `sudo apt install git-lfs`
  - If necessary, install a way to manage Git credentials (see [my notes](https://github.com/haukex/dotfiles/blob/c457de28/Git-Credentials.md))
  - After cloning this repo: `git submodule update --init CardKB/cardkb`
- Misc Notes
  - Camera: `libcamera-still -o ~/Desktop/image.jpg`
  - If an onscreen keyboard is desired: `sudo apt install onboard`


Waveshare 1.3" 240x240 Display Hat
----------------------------------

- `sudo raspi-config`
  - Interfacing Options -> SPI -> No (!)
  - Advanced options -> GL Driver -> Legacy
  - `sudo reboot`
- In `/boot/config.txt` (comment out the last three when connecting external display)

      hdmi_force_hotplug=1
      hdmi_group=2
      hdmi_mode=87
      hdmi_cvt=320 320 60

- <https://github.com/juj/fbcp-ili9341> (only works on 32-bit Raspbian before Bookworm!)

      sudo apt install cmake libraspberrypi-dev
      mkdir -vp ~/code
      cd ~/code
      git clone https://github.com/juj/fbcp-ili9341.git
      # currently at d0ebacf7c1f30b19b50997ebb67ba4f70ab95368
      cd fbcp-ili9341
      mkdir build
      cd build
      # Zero W: (because it doesn't seem to reliably turn the backlight back on?)
      cmake -DWAVESHARE_ST7789VW_HAT=ON -DSPI_BUS_CLOCK_DIVISOR=20 -DSTATISTICS=0 ..
      # Zero 2 W: (seems to need the higher divisor)
      cmake -DWAVESHARE_ST7789VW_HAT=ON -DSPI_BUS_CLOCK_DIVISOR=30 -DBACKLIGHT_CONTROL=ON -DSTATISTICS=0 ..
      make -j
      sudo ./fbcp-ili9341
      sudo install -m 0755 -t /usr/local/sbin fbcp-ili9341
      sudo install -m 0644 -t /etc ../fbcp-ili9341.conf
      sudo install -m 0644 -t /etc/systemd/system ../fbcp-ili9341.service
      sudo systemctl daemon-reload
      sudo systemctl enable fbcp-ili9341 && sudo systemctl start fbcp-ili9341
      rm CMakeCache.txt  # only needed for rebuild

- Possible To-Do for Later: Could optimize the SPI bus frequency (according to the GitHub repo, the max SPI clock is 62.5MHz?)


Waveshare Joystick Mouse
------------------------

Part of the Display Hat (above)

- Waveshare provides a (very inefficent!) script that we can use for testing:
  - note the polling by this script burns ~14% CPU on the Zero W
  - on the Zero 2 W, the pixel step can be decreased from 5 to 3
  - Run the following:

        sudo apt install python3-xlib
        pip install PyUserInput
        mkdir -vp ~/.config/autostart
        ln -snfv 'minicomputer/Docs/Waveshare 1.3inch IPS LCD Hat/Mouse.py' ~/code/Mouse.py
        cat >~/.config/autostart/local.desktop <<EOF
        [Desktop Entry]
        Type=Application
        Exec=python3 /home/haukex/code/Mouse.py
        EOF

- TODO: switch to interrupt-based script and use the better-maintained `python3-uinput` like the CardKB script


I2C for UPS and Keyboard
------------------------

- `sudo raspi-config`, enable I2C
- `sudo apt install i2c-tools`
- Debugging: `sudo i2cdetect -y 1`
  - INA219 should be at 0x43
  - CardKB should be at 0x5f


Waveshare UPS Hat
-----------------

- To test, `python3 'Docs/Waveshare UPS HAT (C)/INA219.py'` (`sudo apt install python3-smbus`)
- It's also possible to use the kernel driver for the same thing:

      sudo modprobe ina2xx
      echo ina219 0x43 | sudo tee /sys/bus/i2c/devices/i2c-1/new_device
      echo 100000 | sudo tee /sys/bus/i2c/devices/1-0043/hwmon/hwmon*/shunt_resistor
      watch -n1 cat /sys/bus/i2c/devices/1-0043/hwmon/hwmon*/{in,curr,power}1_input
      # Units are apparently mV, mA, and uW (and negative current indicates discharging)

- Configuration via device tree:
  - `cd UPS-Hat`
  - `dtc -@ -I dts -O dtb -o ina219-0x43.dtbo ina219-0x43-overlay.dts`
  - `sudo mv -v ina219-0x43.dtbo /boot/overlays/`
  - `sudo vi /boot/config.txt` and add the line `dtoverlay=ina219-0x43`
  - `sudo reboot`
  - `perl -we '$v=qx[cat /sys/bus/i2c/devices/1-0043/hwmon/hwmon*/in1_input]/1000; printf "%.3fV %.1f%%\n", $v, ($v-3)/1.2*100'`
    (this uses the same formula for battery percentage calculation as the above `INA219.py`)

- Possible To-Do for Later: integrate display into UI, though apparently this requires a kernel driver that provides a `/sys/class/power_supply/*`

M5Stack CardKB
--------------

- ATmega8A runs on a wide supply voltage range of 2.7V to 5.5V, so it's fine if we run it off the RPi's 3.3V
- For the connections between the keyboard and the RPi, see the diagram in the `CardKB/cardkb` repo
  - The wires that shipped with my CardKB units are coded as follows:
    - Black = GND
    - Red = VCC
    - Yellow = SDA
    - White = SCL
- `sudo apt install python3-smbus python3-uinput`
- To test, `python3 CardKB/kbd_test.py`
- TODO: Use `CardKB/cardkb`


<!-- vim: set ts=2 sw=2 expandtab : -->
