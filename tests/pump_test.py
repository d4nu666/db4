from machine import Pin, PWM
import time

# =========================
# L298N PUMP TEST
# =========================

# Direction pins
INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)

# Speed pin
# ENA jumper must be removed
# ENA must be connected to GPIO32
ENA = PWM(Pin(32), freq=1000)


def pump_forward(speed):
    """
    speed: 0 to 1023
    """
    speed = max(0, min(1023, speed))

    INA.value(1)
    INB.value(0)
    ENA.duty(speed)

    print("Pump forward | speed:", speed)


def pump_backward(speed):
    """
    Only use this if reversing is safe for your pump.
    """
    speed = max(0, min(1023, speed))

    INA.value(0)
    INB.value(1)
    ENA.duty(speed)

    print("Pump backward | speed:", speed)


def pump_stop():
    ENA.duty(0)
    INA.value(0)
    INB.value(0)

    print("Pump stopped")


# =========================
# TEST SEQUENCE
# =========================

print("Starting L298N pump test")
print("ENA should be connected to GPIO32")
print("ENA jumper must be removed")

pump_stop()
time.sleep(2)

while True:
    pump_forward(500)
    