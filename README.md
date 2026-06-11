# DB4 ESP32 MicroPython Project

This repository contains MicroPython test scripts for an ESP32-based DB4 prototype.

## Files

- `boot.py` - runs on ESP32 boot.
- `main.py` - motor driver test using L298N pins.
- `display.py` - OLED SSD1306 display test.
- `relay.py` - two-channel relay test.
- `thermistor.py` - 10k NTC thermistor temperature reading test.
- `ssd1306.py` - SSD1306 OLED driver.
- `pymakr.conf` - Pymakr project configuration.

## Current pin usage

| Component | ESP32 pin |
|---|---:|
| Relay 1 | GPIO16 |
| Relay 2 | GPIO17 |
| Motor INA | GPIO18 |
| Motor INB | GPIO19 |
| Motor ENA PWM | GPIO25 |
| OLED SDA | GPIO21 |
| OLED SCL | GPIO22 |
| Thermistor ADC | GPIO34 |

## Uploading to ESP32

Use VS Code with Pymakr, Thonny, or `mpremote` to upload the files to the board.

Example with `mpremote`:

```bash
mpremote connect /dev/cu.usbserial-XXX fs cp boot.py :boot.py
mpremote connect /dev/cu.usbserial-XXX fs cp main.py :main.py
mpremote connect /dev/cu.usbserial-XXX fs cp ssd1306.py :ssd1306.py
```

Replace `/dev/cu.usbserial-XXX` with your actual ESP32 port.

## Git setup

```bash
git init
git add .
git commit -m "Initial ESP32 MicroPython project"
```

Then create a GitHub repository and run:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```
