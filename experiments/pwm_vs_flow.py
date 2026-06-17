from machine import Pin, PWM
import time

# ==================================================
# PUMP FLOW CALIBRATION TEST
# Corrected for your real wiring:
# IN1 -> GPIO18
# IN2 -> GPIO19
# ENA -> GPIO32
# ==================================================

# --------------------------
# L298N PUMP PINS
# --------------------------
INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(32), freq=1000)

# --------------------------
# TEST SETTINGS
# --------------------------
LOG_FILE = "flow_calibration.csv"

# Start with high PWM values because your pump may not start at low PWM
PWM_VALUES = [1023, 900, 800, 700, 600, 500]
RUN_TIME_SECONDS = 30
REPEATS = 3

# Pump start boost
BOOST_TIME = 1.0


# ==================================================
# PUMP CONTROL FUNCTIONS
# ==================================================

def pump_off():
    ENA.duty(0)
    INA.value(0)
    INB.value(0)


def pump_forward(pwm_value):
    pwm_value = max(0, min(1023, pwm_value))

    INA.value(1)
    INB.value(0)

    # Full power boost to start the pump
    ENA.duty(1023)
    time.sleep(BOOST_TIME)

    # Then reduce to test PWM
    ENA.duty(pwm_value)


def countdown(seconds):
    for remaining in range(seconds, 0, -1):
        print("Running... {} seconds left".format(remaining))
        time.sleep(1)


# ==================================================
# CSV SETUP
# ==================================================

def create_csv():
    try:
        with open(LOG_FILE, "w") as f:
            f.write("pwm,repeat,run_time_s,volume_ml,flow_rate_ml_min\n")
        print("Created new CSV:", LOG_FILE)
    except OSError as e:
        print("CSV error:", e)


def log_result(pwm, repeat, run_time, volume_ml, flow_rate):
    with open(LOG_FILE, "a") as f:
        f.write("{},{},{},{},{}\n".format(
            pwm,
            repeat,
            run_time,
            volume_ml,
            flow_rate
        ))


# ==================================================
# MAIN TEST
# ==================================================

def run_flow_test():
    print("")
    print("===================================")
    print("PUMP FLOW CALIBRATION TEST STARTED")
    print("===================================")
    print("Pump pins:")
    print("IN1 = GPIO18")
    print("IN2 = GPIO19")
    print("ENA = GPIO32")
    print("")
    print("IMPORTANT:")
    print("Remove ENA jumper from L298N")
    print("Connect ENA to GPIO32")
    print("Connect ESP32 GND to L298N GND")
    print("")
    print("Data will be saved to:", LOG_FILE)
    print("")

    create_csv()
    pump_off()
    time.sleep(2)

    for pwm in PWM_VALUES:
        for repeat in range(1, REPEATS + 1):
            print("")
            print("-----------------------------------")
            print("PWM:", pwm, "| Repeat:", repeat)
            print("-----------------------------------")
            print("Put pump outlet into measuring cup.")
            input("Press ENTER to start this test...")

            print("Starting pump at PWM", pwm)
            pump_forward(pwm)
            countdown(RUN_TIME_SECONDS)
            pump_off()
            print("Pump stopped.")

            volume_text = input("Enter collected volume in mL: ")

            try:
                volume_ml = float(volume_text)
                flow_rate = volume_ml / RUN_TIME_SECONDS * 60.0

                log_result(pwm, repeat, RUN_TIME_SECONDS, volume_ml, flow_rate)

                print("Saved result:")
                print("PWM:", pwm)
                print("Volume:", volume_ml, "mL")
                print("Flow rate:", flow_rate, "mL/min")

            except:
                print("Invalid volume. This result was NOT saved.")

            print("Resting for 5 seconds...")
            time.sleep(5)

    pump_off()
    print("")
    print("===================================")
    print("TEST FINISHED")
    print("CSV saved as:", LOG_FILE)
    print("Download this file from the ESP32.")
    print("===================================")


try:
    run_flow_test()
finally:
    pump_off()