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
              "cooling_pwm,algae_pump,waste_pump,peltier,algae_od,algae_cells,"
              "Am,Aa,Wm,Wa\n")


def log_row(f, elapsed, temp_c, raw, resistance, error, pid_output):
    s = system
    od = s.state["algae_od"]
    cells = s.state["algae_cells"]
    f.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
        int(elapsed), s.state["mode"],
        "" if temp_c is None else round(temp_c, 3),
        "" if raw is None else round(raw, 1),
        "" if resistance is None else round(resistance, 1),
        config.TARGET_TEMP, round(error, 3), round(pid_output, 3),
        s.cooling_pump.duty, s.algae_pump.state, s.waste_pump.state, s.peltier.state,
        "" if od is None else od, "" if cells is None else cells,
        round(s.bio.Am, 4), round(s.bio.Aa, 4), round(s.bio.Wm, 4), round(s.bio.Wa, 4),
    ))


def _log_num(name):
    try:
        return int(name[len(config.LOG_PREFIX):-4])
    except ValueError:
        return -1


def _all_logs():
    try:
        logs = [n for n in os.listdir()
                if n.startswith(config.LOG_PREFIX) and n.endswith(".csv")]
    except OSError:
        return []
    logs.sort(key=_log_num)
    return logs


def next_log_filename():
    """Next db4_log_NNN.csv, always one above the highest existing number."""
    logs = _all_logs()
    highest = _log_num(logs[-1]) if logs else 0
    return "{}{:03d}.csv".format(config.LOG_PREFIX, highest + 1)


def prune_old_logs():
    """Keep only the newest MAX_LOG_FILES logs so the flash never fills up."""
    logs = _all_logs()
    while len(logs) > config.MAX_LOG_FILES:
        old = logs.pop(0)
        try:
            os.remove(old)
            print("Pruned old log:", old)
        except OSError:
            pass


def open_new_log():
    """Start a fresh log file (header written, counter reset, old logs pruned)."""
    name = next_log_filename()
    with open(name, "w") as f:
        f.write(LOG_HEADER)
    system.state["log_file"] = name
    system.state["log_rows"] = 0
    prune_old_logs()
    print("Logging to:", name)
    return name


def make_watchdog():
    """Hardware watchdog so a hang reboots the board (recovers on its own)."""
    if not config.USE_WATCHDOG:
        return None
    try:
        from machine import WDT
        return WDT(timeout=config.WATCHDOG_TIMEOUT_MS)
    except Exception as e:
        print("Watchdog not available:", e)
        return None


def run():
    system.stop_everything()
    time.sleep(2)

    start_web_server()
    log_file = open_new_log()

    print("=" * 40)
    print("DB4 AUTONOMOUS SYSTEM - running constantly")
    print("Target temperature:", config.TARGET_TEMP, "C")
    print("Hold band: {}-{} C".format(config.LOW_TEMP_LIMIT, config.HIGH_TEMP_LIMIT))
    print("=" * 40)

    wdt = make_watchdog()
    pid_output = 0.0
    error = 0.0
    last_od = -1e9

    try:
        while True:
            if wdt is not None:
                wdt.feed()
            try:
                elapsed = time.time() - system.start_time
                if config.RUN_TIME_SECONDS and elapsed >= config.RUN_TIME_SECONDS:
                    print("Run-time limit reached.")
                    break

                raw, resistance, temp_c = system.read_and_update()

                # Read the algae OD sensor periodically (it briefly uses the LED).
                if time.time() - last_od >= config.OD_SAMPLE_INTERVAL:
                    system.read_od()
                    last_od = time.time()

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

                print("t={}s [{}] T={} PWM={} Pel={} Alg={} Was={} Am={} Wm={}".format(
                    int(elapsed), system.state["mode"],
                    "ERR" if temp_c is None else round(temp_c, 2),
                    system.cooling_pump.duty, system.peltier.state,
                    system.algae_pump.state, system.waste_pump.state,
                    round(system.bio.Am, 3), round(system.bio.Wm, 3)))

                with open(log_file, "a") as f:
                    log_row(f, elapsed, temp_c, raw, resistance, error, pid_output)
                system.state["log_rows"] += 1

                # Roll over to a new file when the current one is full.
                if system.state["log_rows"] >= config.MAX_LOG_ROWS:
                    log_file = open_new_log()

            except Exception as e:
                # A transient fault must never stop the bioreactor.
                print("Loop error (continuing):", e)

            time.sleep(config.SAMPLE_TIME)
    finally:
        system.stop_everything()
        print("DB4 control loop ended. Last log:", system.state["log_file"])


if __name__ == "__main__":
    # Keep the system alive: if run() ever exits unexpectedly, restart it.
    while True:
        try:
            run()
            break  # only reached if a RUN_TIME_SECONDS limit is configured
        except KeyboardInterrupt:
            print("Stopped by user.")
            try:
                system.stop_everything()
            except Exception:
                pass
            break
        except Exception as e:
            print("run() crashed; restarting in 3 s:", e)
            try:
                system.stop_everything()
            except Exception:
                pass
            time.sleep(3)
