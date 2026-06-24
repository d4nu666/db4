# =========================
# DB4 threaded web-server handler (experimental).
#
# Usage:
#   from web_server_threaded import StartServer, SendMessage
# Start the server, then push updates to the client with
#   SendMessage(messageType, message)
# The web page must handle the |type|message| request protocol.
#
# NOTE: this is the message-based server experiment. Pins now come
# from config.py (single source of truth). Protocol mapping on the
# current hardware: the FAN command drives the single relay
# (GPIO16, Peltier/cooling) and the PUMP command drives the algae
# pump (GPIO23). WiFi credentials come from secrets.py.
# =========================

import network
import socket
import time
from machine import Pin, I2C

import config

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    raise ImportError("Create secrets.py from secrets_example.py with your WiFi details.")

# =========================
# PINS - all sourced from config.py
# =========================

# Single relay channel (Peltier / cooling), active LOW.
relay = Pin(config.PELTIER_RELAY_PIN, Pin.OUT)
relay.value(config.PELTIER_OFF)     # OFF at start

# RGB LED pins
red = Pin(config.LED_R_PIN, Pin.OUT)
green = Pin(config.LED_G_PIN, Pin.OUT)
blue = Pin(config.LED_B_PIN, Pin.OUT)

# Pump control (mapped to the algae pump on this hardware).
pump = Pin(config.ALGAE_PUMP_PIN, Pin.OUT)
pump.value(config.ALGAE_PUMP_OFF)

# I2C: OLED + TCS34725
i2c = I2C(0, scl=Pin(config.I2C_SCL), sda=Pin(config.I2C_SDA), freq=config.I2C_FREQ)

# =========================
# SYSTEM STATE
# =========================

system_state = {
    "pump": "OFF",
    "fan": "OFF",
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
    pump.value(config.ALGAE_PUMP_ON)
    system_state["pump"] = "ON"

def pump_off():
    pump.value(config.ALGAE_PUMP_OFF)
    system_state["pump"] = "OFF"

def fan_on():
    relay.value(config.PELTIER_ON)
    system_state["fan"] = "ON"

def fan_off():
    relay.value(config.PELTIER_OFF)
    system_state["fan"] = "OFF"

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
# START PROGRAM
# =========================

rgb_off()
update_sensors()
pendingMessages = {"temperature": "0"}

def SendMessage(requestType, message):
    request = "|" + requestType + "|" + message + "|"
    pendingMessages[requestType] = message

# handles the raw request string
def HandlePendingRequest(request):
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
                HandlePendingRequest(enumerate(request.split())[index])
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

def HandlePendingMessages(connection):
    for requestType, message in pendingMessages.items():
        finalMessage = "|" + requestType + "|" + message + "|"
        try:
            connection.send(finalMessage)
        except Exception as e:
            print("Error sending message:", e)
            connection.close()
            connection = None

def HandleConnections(server): # needs to just add to existing connections so that events are handled in main loop
    connection = None
    while True:
        if connection is None:
            connection = server.accept() # this will block until a client connects
        try:
            HandlePendingMessages(connection)
            maybe_update_sensors()

            request = connection.recv(4096) # reads a max of 4096 bytes from the client
            request = str(request) # turns the request from binary into a string
            HandlePendingRequest(request) # handles the requests made to server

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
