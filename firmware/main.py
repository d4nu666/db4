# ============================================================
# DB4 Mussel Bioreactor - autonomous controller (headless).
#
# Responsibilities:
#   - read tank temperature (thermistor)
#   - regulate it with a cooling PID + peltier
#   - run the biological algae/waste scheduler
#   - show status on the OLED and RGB LED
#   - log everything to CSV
#
# Hardware details live in config.py. Drivers live in lib/.
# For interactive web control instead, run webserver.py.
# ============================================================

import time
from machine import Pin, I2C

import config
from thermistor import Thermistor
from pid import CoolingPID
from bio_model import BioController
import actuators

# ---- hardware -------------------------------------------------
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


def stop_everything():
    peltier.off()
    waste_pump.off()
    algae_pump.off()
    cooling_pump.off()
    led.off()


def apply_temperature_control(temp_c):
    """Drive the cooling pump from the PID. Returns (pid_output, error)."""
    peltier.on()

    if temp_c is None:
        cooling_pump.off()
        return 0.0, 0.0

    if temp_c <= config.PUMP_FORCE_OFF_TEMP:
        cooling_pump.off()
        return 0.0, temp_c - config.TARGET_TEMP

    if temp_c >= config.PUMP_FULL_ON_TEMP:
        cooling_pump.set(config.MAX_COOLING_PWM)
        return 100.0, temp_c - config.TARGET_TEMP

    pid_output, error = pid.update(temp_c)
    if pid_output <= 0:
        cooling_pump.off()
    else:
        pwm_span = config.MAX_COOLING_PWM - config.MIN_COOLING_PWM
        cooling_pump.set(config.MIN_COOLING_PWM + (pid_output / 100.0) * pwm_span)
    return pid_output, error


def update_status_led(temp_c):
    if temp_c is None:
        led.red()
    elif temp_c < config.LOW_TEMP_LIMIT:
        led.blue()
    elif temp_c > config.HIGH_TEMP_LIMIT:
        led.red()
    else:
        led.green()


def update_oled(temp_c):
    if oled is None:
        return
    try:
        oled.fill(0)
        oled.text("DB4 Bio Control", 0, 0)
        oled.text("Temp: ERROR" if temp_c is None else "T:{:.2f} C".format(temp_c), 0, 12)
        oled.text("PWM:{}".format(cooling_pump.duty), 0, 24)
        oled.text("A:{:.2f} W:{:.2f}".format(bio.Am, bio.Wm), 0, 36)
        oled.text("Alg:{} Was:{}".format(algae_pump.state, waste_pump.state), 0, 48)
        oled.show()
    except Exception as e:
        print("OLED update error:", e)


LOG_HEADER = ("time_s,temp_c,raw_adc,resistance_ohm,target_c,error,pid_output,"
              "cooling_pwm,algae_pump,waste_pump,Am,Aa,Wm,Wa\n")


def log_row(f, elapsed, temp_c, raw, resistance, error, pid_output):
    f.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
        int(elapsed),
        "" if temp_c is None else round(temp_c, 3),
        "" if raw is None else round(raw, 1),
        "" if resistance is None else round(resistance, 1),
        config.TARGET_TEMP, round(error, 3), round(pid_output, 3),
        cooling_pump.duty, algae_pump.state, waste_pump.state,
        round(bio.Am, 4), round(bio.Aa, 4), round(bio.Wm, 4), round(bio.Wa, 4),
    ))


def run():
    stop_everything()
    time.sleep(2)
    peltier.on()

    print("=" * 40)
    print("DB4 FINAL AUTONOMOUS SYSTEM")
    print("Target temperature:", config.TARGET_TEMP, "C")
    print("Log file:", config.LOG_FILE)
    print("=" * 40)

    start_time = time.time()
    with open(config.LOG_FILE, "w") as f:
        f.write(LOG_HEADER)

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= config.RUN_TIME_SECONDS:
                print("Experiment finished.")
                break

            raw, resistance, temp_c = thermistor.read()
            pid_output, error = apply_temperature_control(temp_c)
            update_status_led(temp_c)
            bio.update(elapsed)
            update_oled(temp_c)

            print("t={}s T={} PWM={} Alg={} Was={} Am={} Wm={}".format(
                int(elapsed),
                "ERR" if temp_c is None else round(temp_c, 2),
                cooling_pump.duty, algae_pump.state, waste_pump.state,
                round(bio.Am, 3), round(bio.Wm, 3)))

            with open(config.LOG_FILE, "a") as f:
                log_row(f, elapsed, temp_c, raw, resistance, error, pid_output)

            time.sleep(config.SAMPLE_TIME)

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        stop_everything()
        print("DB4 SYSTEM STOPPED SAFELY. Log saved as:", config.LOG_FILE)


if __name__ == "__main__":
    run()
