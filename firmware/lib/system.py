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

# ---- optional OLED -------------------------------------------
oled = None
try:
    import ssd1306
    i2c = I2C(0, scl=Pin(config.I2C_SCL), sda=Pin(config.I2C_SDA), freq=config.I2C_FREQ)
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    oled.fill(0)
    oled.text("DB4 System", 0, 0)
    oled.text("Starting...", 0, 12)
    oled.show()
except Exception as e:
    print("OLED not used:", e)
    oled = None

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
    "pid_output": 0.0,
    "uptime_s": 0,
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
    state["uptime_s"] = int(time.time() - start_time)
    return raw, resistance, temp_c


# ---- autonomous temperature control (auto mode only) ---------
def autonomous_temperature(temp_c):
    """Cooling PID. Returns (pid_output, error). Updates state."""
    peltier.on()

    if temp_c is None:
        cooling_off()
        state["pid_output"] = 0.0
        return 0.0, 0.0

    if temp_c <= config.PUMP_FORCE_OFF_TEMP:
        cooling_off()
        state["pid_output"] = 0.0
        return 0.0, temp_c - config.TARGET_TEMP

    if temp_c >= config.PUMP_FULL_ON_TEMP:
        cooling_set(config.MAX_COOLING_PWM)
        state["pid_output"] = 100.0
        return 100.0, temp_c - config.TARGET_TEMP

    pid_output, error = pid.update(temp_c)
    if pid_output <= 0:
        cooling_off()
    else:
        span = config.MAX_COOLING_PWM - config.MIN_COOLING_PWM
        cooling_set(config.MIN_COOLING_PWM + (pid_output / 100.0) * span)
    state["pid_output"] = pid_output
    return pid_output, error
