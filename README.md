# DB4 ESP32 MicroPython Project

This project contains the MicroPython code for the DB4 ESP32 prototype.  
The system is built around an ESP32 board and controls/reads:

- OLED SSD1306 display
- 2-channel relay module
- Fan relay
- Heating/cooling relay
- L298N motor driver for the pump
- 10k NTC thermistor temperature sensor
- RGB LED test module
- Basic PID control logic draft

The project is developed and uploaded using **VS Code with the Pymakr extension**.

---

## Project structure

| File | Purpose |
|---|---|
| `boot.py` | Runs automatically when the ESP32 boots. It imports `main` and starts `main.run_system()`. |
| `main.py` | Main DB4 system program. Controls fan relay, heating relay, pump motor, thermistor reading, and OLED display. |
| `display.py` | Standalone OLED SSD1306 display test. |
| `relay.py` | Standalone relay test for the 2-channel relay module. |
| `thermistor.py` | Standalone temperature test using the 10k NTC thermistor on GPIO34. |
| `LED_test.py` | Standalone RGB LED test using GPIO25, GPIO26, and GPIO27. |
| `pid.py` | PID control draft for temperature and OD control logic. |
| `ssd1306.py` | MicroPython driver library for the OLED display. |
| `pymakr.conf` | Pymakr configuration file for uploading/running code from VS Code. |
| `README.md` | Project documentation. |

---

## Pin schema

These are the pins currently used in the uploaded code.

| ESP32 pin | Used by | File(s) | Function |
|---|---|---|---|
| **GPIO16** | Relay module IN2 | `main.py`, `relay.py` | Heating/cooling relay control |
| **GPIO17** | Relay module IN1 | `main.py`, `relay.py` | Fan relay control |
| **GPIO18** | L298N motor driver | `main.py` | Pump `INA` direction input |
| **GPIO19** | L298N motor driver | `main.py` | Pump `INB` direction input |
| **GPIO21** | OLED display | `main.py`, `display.py` | I2C `SDA` |
| **GPIO22** | OLED display | `main.py`, `display.py` | I2C `SCL` |
| **GPIO25** | L298N motor driver / RGB LED red | `main.py`, `LED_test.py` | Pump PWM `ENA` in `main.py`; red LED in `LED_test.py` |
| **GPIO26** | RGB LED green | `LED_test.py` | Green LED output |
| **GPIO27** | RGB LED blue | `LED_test.py` | Blue LED output |
| **GPIO34** | Thermistor | `main.py`, `thermistor.py` | ADC input for temperature reading |
| **3V3** | Thermistor circuit / sensors | Hardware wiring | 3.3 V supply |
| **5V / VIN** | Relay/OLED modules if needed | Hardware wiring | 5 V supply from ESP32 board or external supply |
| **GND** | All modules | Hardware wiring | Common ground |

---

## Important pin note

`GPIO25` is used in two different ways:

- In `main.py`, GPIO25 is used as the **PWM ENA pin for the L298N pump driver**.
- In `LED_test.py`, GPIO25 is used as the **red LED pin**.

This is okay because `LED_test.py` is only a standalone test file.  
Do **not** run the LED test while the pump driver is connected to GPIO25 unless you intentionally want to test that pin.

---

## Relay logic

The relay module is **active LOW**.

That means:

```python
relay.value(0)  # ON
relay.value(1)  # OFF
```

Current relay mapping:

| Relay input | ESP32 pin | Purpose |
|---|---|---|
| IN1 | GPIO17 | Fan relay |
| IN2 | GPIO16 | Heating/cooling relay |

In `main.py`, the fan is forced ON continuously:

```python
fan_relay.value(0)
```

The heating/cooling relay is kept OFF:

```python
heat_relay.value(1)
```

---

## OLED display wiring

The OLED uses I2C.

| OLED pin | ESP32 connection |
|---|---|
| VCC | 3V3 or 5V, depending on the OLED module |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

The OLED is initialized in the code as:

```python
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
```

---

## Pump motor driver wiring

The pump is controlled through an L298N motor driver.

| L298N pin | ESP32 connection |
|---|---|
| INA | GPIO18 |
| INB | GPIO19 |
| ENA | GPIO25 PWM |
| GND | Common GND |
| Motor output | Pump motor |
| Motor supply | External motor power supply |

Pump control in `main.py`:

```python
def pump_on(speed=900):
    INA.value(1)
    INB.value(0)
    ENA.duty(speed)

def pump_off():
    INA.value(0)
    INB.value(0)
    ENA.duty(0)
```

---

## Thermistor wiring

The thermistor uses GPIO34 as an ADC input.

Current voltage divider wiring:

```text
3V3 -> 10k fixed resistor -> GPIO34 -> thermistor -> GND
```

GPIO34 is input-only, which is fine because it is only used for analog reading.

Thermistor constants used:

```python
SERIES_RESISTOR = 10000
THERMISTOR_NOMINAL = 10000
TEMPERATURE_NOMINAL = 25
BETA = 3950
```

---

## RGB LED test wiring

Used only in `LED_test.py`.

| RGB LED channel | ESP32 pin |
|---|---|
| Red | GPIO25 |
| Green | GPIO26 |
| Blue | GPIO27 |

The test turns on red, green, blue, and white-ish one after another.

---

## Boot behavior

`boot.py` automatically starts the main system:

```python
import main

main.run_system()
```

This means when the ESP32 powers on or resets, it will start the DB4 system without manually running `main.py`.

---

## How to upload using Pymakr

This project is intended to be used with **VS Code + Pymakr**.

Basic workflow:

1. Open this project folder in VS Code.
2. Connect the ESP32 by USB.
3. Select the correct serial port in Pymakr.
4. Upload the project files to the ESP32.
5. Reset the ESP32.
6. `boot.py` will automatically start `main.run_system()`.

Make sure these files are uploaded to the board:

```text
boot.py
main.py
ssd1306.py
```

Upload the test files only when you need them:

```text
display.py
relay.py
thermistor.py
LED_test.py
pid.py
```

---

## Current main system behavior

When `main.py` runs:

1. Fan relay turns ON immediately.
2. Heating/cooling relay stays OFF.
3. OLED display starts.
4. Thermistor temperature is read from GPIO34.
5. Pump turns ON for 5 seconds.
6. Pump turns OFF for 5 seconds.
7. OLED shows:
   - DB4 system name
   - Fan state
   - Pump state
   - Temperature
   - ADC value
8. The loop repeats forever.

---

## Safety notes

- Always use a **common GND** between ESP32, relay module, L298N, sensors, and external power supply.
- Do not connect 5 V signals directly to ESP32 GPIO pins.
- Keep power supplies away from water.
- Check wiring before powering the pump or relay.
- The relay is active LOW, so the logic is reversed.
- GPIO25 has a conflict between the pump PWM and LED test, so use only one purpose at a time.

---

## Current pin constants

```python
FAN_RELAY = 17
HEAT_RELAY = 16

OLED_SDA = 21
OLED_SCL = 22

PUMP_INA = 18
PUMP_INB = 19
PUMP_ENA_PWM = 25

THERMISTOR_ADC = 34

LED_RED = 25
LED_GREEN = 26
LED_BLUE = 27
```
