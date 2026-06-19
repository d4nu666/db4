from machine import Pin, PWM
import time

# ==================================================
# EMERGENCY STOP PROGRAM
# Stops pump, fan/cooling relay, and RGB LED
# ==================================================

# Fan / cooling relay on GPIO16
# Your latest relay logic:
# 1 = ON
# 0 = OFF
fan_relay = Pin(16, Pin.OUT)

# Pump L298N motor driver
INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(32), freq=1000)

# RGB LED
rgb_red = PWM(Pin(25), freq=1000)
rgb_green = PWM(Pin(26), freq=1000)
rgb_blue = PWM(Pin(27), freq=1000)


def stop_everything():
    # Stop pump
    ENA.duty(0)
    INA.value(0)
    INB.value(0)

    # Stop fan / cooling relay
    fan_relay.value(0)

    # Turn RGB LED off
    rgb_red.duty(0)
    rgb_green.duty(0)
    rgb_blue.duty(0)

    print("EVERYTHING STOPPED")
    print("Pump OFF")
    print("Fan/Cooling OFF")
    print("RGB LED OFF")


# Run stop immediately
stop_everything()

# Keep everything stopped forever
while True:
    stop_everything()
    time.sleep(1)