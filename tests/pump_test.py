from machine import Pin, PWM
import time

INA_PIN = 18
INB_PIN = 19
ENA_PIN = 32

ina = Pin(INA_PIN, Pin.OUT)
inb = Pin(INB_PIN, Pin.OUT)
ena = PWM(Pin(ENA_PIN), freq=1000)

def pump_stop():
    ina.value(0)
    inb.value(0)
    ena.duty(0)

def pump_forward(speed):
    ina.value(1)
    inb.value(0)
    ena.duty(speed)

print("Pump L298N test started")
print("INA = GPIO18")
print("INB = GPIO19")
print("ENA PWM = GPIO32")

while True:
    print("Pump ON at PWM 500")
    pump_forward(500)
    time.sleep(5)

    print("Pump OFF")
    pump_stop()
    time.sleep(5)