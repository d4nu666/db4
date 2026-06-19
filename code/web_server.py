import network
import socket
import time
from machine import Pin, I2C

# =========================
# WIFI SETTINGS
# =========================
WIFI_SSID = "bam"
WIFI_PASSWORD = "greenflame31052004"

# =========================
# PINS - DO NOT CHANGE
# =========================

# Relay module
heat_relay = Pin(16, Pin.OUT)   # Relay IN1
fan_relay = Pin(17, Pin.OUT)    # Relay IN2

# Relay is ACTIVE LOW:
# 0 = ON
# 1 = OFF
heat_relay.value(1)     # OFF at start
fan_relay.value(0)      # Fan ON at start

# RGB LED pins
red = Pin(25, Pin.OUT)
green = Pin(26, Pin.OUT)
blue = Pin(27, Pin.OUT)

# Pump / L298N control pin
pump = Pin(18, Pin.OUT)
pump.value(0)

# I2C: OLED + TCS34725
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

# =========================
# SYSTEM STATE
# =========================

system_state = {
    "pump": "OFF",
    "fan": "ON",
    "heat": "OFF",
    "rgb": "OFF",
    "temperature": "N/A",
    "red_value": 0,
    "green_value": 0,
    "blue_value": 0,
    "clear_value": 0,
    "i2c_devices": ""
}

last_sensor_update = 0

# =========================
# RGB LED FUNCTIONS
# =========================

def rgb_off():
    red.value(0)
    green.value(0)
    blue.value(0)
    system_state["rgb"] = "OFF"

def rgb_red():
    red.value(1)
    green.value(0)
    blue.value(0)
    system_state["rgb"] = "RED"

def rgb_green():
    red.value(0)
    green.value(1)
    blue.value(0)
    system_state["rgb"] = "GREEN"

def rgb_blue():
    red.value(0)
    green.value(0)
    blue.value(1)
    system_state["rgb"] = "BLUE"

def rgb_white():
    red.value(1)
    green.value(1)
    blue.value(1)
    system_state["rgb"] = "WHITE"

# =========================
# ACTUATOR FUNCTIONS
# =========================

def pump_on():
    pump.value(1)
    system_state["pump"] = "ON"

def pump_off():
    pump.value(0)
    system_state["pump"] = "OFF"

def fan_on():
    fan_relay.value(0)
    system_state["fan"] = "ON"

def fan_off():
    fan_relay.value(1)
    system_state["fan"] = "OFF"

def heat_on():
    heat_relay.value(0)
    system_state["heat"] = "ON"

def heat_off():
    heat_relay.value(1)
    system_state["heat"] = "OFF"

# =========================
# SENSOR UPDATE
# Replace this with your real thermistor + TCS34725 code later
# =========================

def update_sensors():
    try:
        devices = i2c.scan()
        system_state["i2c_devices"] = str([hex(d) for d in devices])
    except:
        system_state["i2c_devices"] = "I2C error"

    # Placeholder values for now
    # Later replace these with real sensor readings
    system_state["temperature"] = "22.5"
    system_state["red_value"] = 100
    system_state["green_value"] = 120
    system_state["blue_value"] = 140
    system_state["clear_value"] = 300

def maybe_update_sensors():
    global last_sensor_update

    now = time.ticks_ms()

    # Update sensors only once every 1000 ms
    if time.ticks_diff(now, last_sensor_update) > 1000:
        update_sensors()
        last_sensor_update = now

# =========================
# WIFI CONNECT
# =========================

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            print(".")
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("Connected!")
        print("Open this in browser:")
        print("http://" + ip)
        return ip
    else:
        print("WiFi connection failed")
        return None

# =========================
# SERVER COMMUNICATIONS
# =========================



# =========================
# FAST RESPONSES
# ========================= old http protocols

# =========================
# WEB SERVER FUNCTIONS
# =========================


# =========================
# START PROGRAM
# =========================

rgb_off()
update_sensors()

# handles the raw request string
def HandleStringRequest(request):
    start = False
    mid = False
    end = False
    messageType = ""
    message = ""
    
    for index, character in enumerate(request.split()):
        if character == "|":
            if not start:
                start = True
            elif not mid:
                mid = True
            elif not end:
                end = True
            else:
                HandleStringRequest(enumerate(request.split())[index])
        else:
            if start and not mid:
                messageType += character
            elif mid and not end:
                message += character

    #error handling for invalid requests
    if not start or not mid or not end:
        print("Invalid request format: ", request)
    if messageType == "" or message == "":
        print("Invalid request content: ", request)
        return

    match messageType: # add any other extra request types into here with their respective funcitons
        case "PUMP":
            if message == "ON":
                pump_on()
            elif message == "OFF":
                pump_off()
        case "FAN":
            if message == "ON":
                fan_on()
            elif message == "OFF":
                fan_off()
        case "RGB":
            match message:
                case "RED":
                    rgb_red()
                case "GREEN":
                    rgb_green()
                case "BLUE":
                    rgb_blue()
                case "WHITE":
                    rgb_white()
                case "OFF":
                    rgb_off()
        case "PID":
            match message:
                case "restart":
                    pass
                case "off":
                    pass
connection = None
def HandleConnections(server): # needs to just add to existing connections so that events are handled in main loop
    
    while True:
        if connection is None:
            connection = server.accept() # this will block until a client connects
        try:
            maybe_update_sensors()

            request = connection.recv(512) # reads a max of 512 bytes from the client
            request = str(request) # turns the request from binary into a string
            HandleStringRequest(request) # handles the requests made to server

        except Exception as e:
            print("Server error:", e)
            try:
                connection.close()
            except:
                pass
            finally:
                connection = None

def StartServer():
    ip = connect_wifi()

    if ip is None:
        return
    
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    print("mussel farm controller running on the ip: " + ip)
    
    HandleConnections(s)

