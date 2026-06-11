from machine import Pin, PWM
import time

INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(25), freq=1000)

def motor_forward(speed):
    INA.value(1)
    INB.value(0)
    ENA.duty(speed)  # 0 to 1023
    print("Motor forward:", speed)

def motor_stop():
    INA.value(0)
    INB.value(0)
    ENA.duty(0)
    print("Motor stop")

print("FAST motor test started")

while True:
    motor_forward(1023)   # full speed
    time.sleep(5)

    motor_stop()
    time.sleep(2)