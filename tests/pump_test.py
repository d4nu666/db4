from machine import Pin, PWM
import time


ENA_PIN = 32


ena = PWM(Pin(ENA_PIN), freq=1000)



def pump_forward(speed):    
    ena.duty(speed)

print("Pump L298N test started")
print("INA = GPIO18")
print("INB = GPIO19")
print("ENA PWM = GPIO32")

while True:
    print("Pump ON at PWM 1023")
    pump_forward(1023)
    time.sleep(5)

    print("Pump OFF")
    ena.duty(0)
    time.sleep(5)