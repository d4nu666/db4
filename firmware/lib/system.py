# ============================================================
# DB4 shared system layer.
#
# Owns the hardware objects and the live system state so that the
# autonomous control loop (main.py) and the web dashboard
# (webserver.py) operate on ONE set of pins with a single control
# authority. Importing this module initialises the hardware once.
#
# Control authority:
#   state["mode"] == "auto"   -> main.py runs the PID + bio scheduler
#   state["mode"] == "manual" -> autonomous control is paused; the
#                                dashboard's manual commands stick.
# ============================================================

import time
from machine import Pin, I2C

import config
from thermistor import Thermistor
from pid import CoolingPID
from bio_model import BioController
from od_sensor import TCS34725, ODSensor, AlgaeODModel
import actuators

# ---- hardware singletons (initialised once) ------------------
thermistor = Thermistor()
cooling_pump = actuators.CoolingPump()
algae_pump = actuators.make_algae_pump()
waste_pump = actuators.make_waste_pump()
peltier = actuators.make_peltier()
led = actuators.StatusLED()

pid = CoolingPID()
bio = BioController(algae_pump, waste_pump)

# ---- I2C bus (shared by OLED + TCS34725 OD sensor) ----------
i2c = None
oled = None
od_sensor = None
algae_model = AlgaeODModel()

try:
    i2c = I2C(0, scl=Pin(config.I2C_SCL), sda=Pin(config.I2C_SDA), freq=config.I2C_FREQ)
except Exception as e:
    print("I2C bus not available:", e)

if i2c is not None:
    try:
        import ssd1306
        oled = ssd1306.SSD1306_I2C(128, 64, i2c)
        oled.fill(0)
        oled.text("DB4 System", 0, 0)
        oled.text("Starting...", 0, 12)
        oled.show()
    except Exception as e:
        print("OLED not used:", e)
        oled = None
    try:
        od_sensor = ODSensor(TCS34725(i2c), light=led)
    except Exception as e:
        print("OD sensor not used:", e)
        od_sensor = None

# ---- shared state --------------------------------------------
start_time = time.time()

state = {
    "mode": "auto",                       # "auto" or "manual"
    "temperature": None,
    "raw_adc": 0,
    "target_temp": config.TARGET_TEMP,
    "cooling_pump": False,
    "cooling_pwm": config.MIN_COOLING_PWM,
    "algae_pump": False,
    "waste_pump": False,
    "peltier": False,
    "algae_od": None,
    "algae_cells": None,
    "pid_output": 0.0,
    "uptime_s": 0,
    "log_rows": 0,
    "log_file": "",
}


# ---- mode ----------------------------------------------------
def set_mode(mode):
    state["mode"] = "manual" if mode == "manual" else "auto"
    if state["mode"] == "auto":
        pid.reset()      # avoid an integral jump when control resumes


# ---- actuator helpers (drive hardware AND update state) ------
def cooling_set(duty):
    cooling_pump.set(duty)
    state["cooling_pwm"] = cooling_pump.duty
    state["cooling_pump"] = cooling_pump.is_on


def cooling_off():
    cooling_pump.off()
    state["cooling_pump"] = False


def algae_on():
    algae_pump.on()
    state["algae_pump"] = True


def algae_off():
    algae_pump.off()
    state["algae_pump"] = False


def waste_on():
    waste_pump.on()
    state["waste_pump"] = True


def waste_off():
    waste_pump.off()
    state["waste_pump"] = False


def stop_everything():
    peltier.off()
    cooling_off()
    algae_off()
    waste_off()
    led.off()


def emergency_stop():
    # Force manual so the autonomous loop will not restart anything.
    set_mode("manual")
    stop_everything()


# ---- sensing -------------------------------------------------
def read_and_update():
    """Read the thermistor and refresh shared state. Returns the raw tuple."""
    raw, resistance, temp_c = thermistor.read()
    state["raw_adc"] = 0 if raw is None else int(raw)
    state["temperature"] = None if temp_c is None else round(temp_c, 2)
    state["peltier"] = bool(peltier.state)
    state["uptime_s"] = int(time.time() - start_time)
    return raw, resistance, temp_c


def read_od():
    """Read the OD sensor, store algae OD + concentration in state.
    Returns cells/mL, or None if no sensor is connected."""
    if od_sensor is None:
        return None
    try:
        data = od_sensor.read_od()
        od_mean = data["od_mean"]
        cells = algae_model.od_to_cells_ml(od_mean)
        state["algae_od"] = round(od_mean, 4)
        state["algae_cells"] = None if cells is None else int(cells)
        led.off()          # turn the illumination LED back off
        return cells
    except Exception as e:
        print("OD read error:", e)
        return None


# ---- cooling helpers -----------------------------------------
def cooling_all_on():
    """Too hot: turn the Peltier and cooling pump fully on."""
    peltier.on()
    state["peltier"] = True
    cooling_set(config.MAX_COOLING_PWM)


def cooling_all_off():
    """Too cold (or safe stop): turn the Peltier and cooling pump off."""
    peltier.off()
    state["peltier"] = False
    cooling_off()


# ---- autonomous temperature control (auto mode only) ---------
def autonomous_temperature(temp_c):
    """Hysteresis (on/off) control to hold the tank in
    [LOW_TEMP_LIMIT, HIGH_TEMP_LIMIT] (17-18 C):

      temp >= HIGH_TEMP_LIMIT  -> Peltier + pump fully ON  (too hot)
      temp <= LOW_TEMP_LIMIT   -> Peltier + pump OFF        (too cold)
      in between               -> hold the current state    (no chatter)

    Returns (output_pct, error).
    """
    if temp_c is None:
        cooling_all_off()            # sensor failure -> safe
        state["pid_output"] = 0.0
        return 0.0, 0.0

    error = temp_c - config.TARGET_TEMP

    if temp_c >= config.HIGH_TEMP_LIMIT:
        cooling_all_on()
        state["pid_output"] = 100.0
    elif temp_c <= config.LOW_TEMP_LIMIT:
        cooling_all_off()
        state["pid_output"] = 0.0
    # else: inside the 17-18 C band -> leave Peltier/pump as they are

    return state["pid_output"], error
