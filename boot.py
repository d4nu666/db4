# ============================================================
# DB4 Mussel Bioreactor - main entry point.
#
# On boot this:
#   - starts the web dashboard (webserver.py) on a background thread
#   - runs the autonomous control loop (temperature PID + biological
#     scheduler + logging) on the main thread
#
# Both share one set of hardware via system.py. The dashboard's
# "Manual mode" pauses the autonomous control so manual commands
# stick; "Auto" hands control back. Emergency stop always works.
#
# Hardware details live in config.py. Drivers live in lib/.
# ============================================================

import time
import sys
import os
from machine import Pin

# ==================================================
# Import path fix
# Works whether files are uploaded to / or /firmware
# ==================================================

try:
    os.chdir("/firmware")
except OSError:
    pass

for path in ["/", "/lib", "/firmware", "/firmware/lib"]:
    if path not in sys.path:
        sys.path.append(path)

import config
import system


def start_web_server():
    """Launch the web dashboard on a background thread (best-effort)."""
    try:
        import _thread
        import webserver
        try:
            _thread.stack_size(16 * 1024)
        except Exception:
            pass
        _thread.start_new_thread(webserver.serve, ())
        print("Web dashboard thread started")
    except Exception as e:
        # No WiFi / no secrets.py / no threads: control loop still runs.
        print("Web dashboard not started:", e)


def update_status_led(temp_c):
    if temp_c is None:
        system.led.red()
    elif temp_c < config.LOW_TEMP_LIMIT:
        system.led.blue()
    elif temp_c > config.HIGH_TEMP_LIMIT:
        system.led.red()
    else:
        system.led.green()


def update_oled(temp_c):
    if system.oled is None:
        return
    try:
        oled = system.oled
        oled.fill(0)
        oled.text("DB4 " + system.state["mode"], 0, 0)
        oled.text("Temp: ERROR" if temp_c is None else "T:{:.2f} C".format(temp_c), 0, 12)
        oled.text("PWM:{}".format(system.cooling_pump.duty), 0, 24)
        oled.text("A:{:.2f} W:{:.2f}".format(system.bio.Am, system.bio.Wm), 0, 36)
        oled.text("Alg:{} Was:{}".format(system.algae_pump.state, system.waste_pump.state), 0, 48)
        oled.show()
    except Exception as e:
        print("OLED update error:", e)


LOG_HEADER = ("time_s,mode,temp_c,raw_adc,resistance_ohm,target_c,error,pid_output,"
              "cooling_pwm,algae_pump,waste_pump,Am,Aa,Wm,Wa\n")


def log_row(f, elapsed, temp_c, raw, resistance, error, pid_output):
    s = system
    f.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
        int(elapsed), s.state["mode"],
        "" if temp_c is None else round(temp_c, 3),
        "" if raw is None else round(raw, 1),
        "" if resistance is None else round(resistance, 1),
        config.TARGET_TEMP, round(error, 3), round(pid_output, 3),
        s.cooling_pump.duty, s.algae_pump.state, s.waste_pump.state,
        round(s.bio.Am, 4), round(s.bio.Aa, 4), round(s.bio.Wm, 4), round(s.bio.Wa, 4),
    ))


def run():
    system.stop_everything()
    time.sleep(2)
    system.peltier.on()

    start_web_server()

    print("=" * 40)
    print("DB4 FINAL AUTONOMOUS SYSTEM")
    print("Target temperature:", config.TARGET_TEMP, "C")
    print("Log file:", config.LOG_FILE)
    print("=" * 40)

    with open(config.LOG_FILE, "w") as f:
        f.write(LOG_HEADER)

    pid_output = 0.0
    error = 0.0

    try:
        while True:
            elapsed = time.time() - system.start_time
            if elapsed >= config.RUN_TIME_SECONDS:
                print("Experiment finished.")
                break

            raw, resistance, temp_c = system.read_and_update()

            if system.state["mode"] == "auto":
                # Autonomous control owns the actuators.
                pid_output, error = system.autonomous_temperature(temp_c)
                system.bio.update(elapsed)
            else:
                # Manual mode: dashboard owns the actuators, do not override.
                pid_output = system.state["pid_output"]
                error = 0.0

            update_status_led(temp_c)
            update_oled(temp_c)

            print("t={}s [{}] T={} PWM={} Alg={} Was={} Am={} Wm={}".format(
                int(elapsed), system.state["mode"],
                "ERR" if temp_c is None else round(temp_c, 2),
                system.cooling_pump.duty, system.algae_pump.state,
                system.waste_pump.state, round(system.bio.Am, 3), round(system.bio.Wm, 3)))

            with open(config.LOG_FILE, "a") as f:
                log_row(f, elapsed, temp_c, raw, resistance, error, pid_output)

            time.sleep(config.SAMPLE_TIME)

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        system.stop_everything()
        print("DB4 SYSTEM STOPPED SAFELY. Log saved as:", config.LOG_FILE)


if __name__ == "__main__":
    run()
