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
# WEB PAGE
# =========================

def web_page():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>DB4 ESP32 Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial;
            background: #f2f2f2;
            padding: 12px;
        }
        .card {
            background: white;
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
        }
        button {
            padding: 12px;
            margin: 4px;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            background: #1976d2;
            color: white;
        }
        .on {
            background: #2e7d32;
        }
        .off {
            background: #555555;
        }
        .danger {
            background: #c62828;
        }
    </style>
</head>

<body>
    <h1>DB4 ESP32 Control</h1>

    <div class="card">
        <h2>Sensor Readings</h2>
        <p><b>Temperature:</b> """ + str(system_state["temperature"]) + """ °C</p>
        <p><b>RGB sensor:</b></p>
        <p>R: """ + str(system_state["red_value"]) + """</p>
        <p>G: """ + str(system_state["green_value"]) + """</p>
        <p>B: """ + str(system_state["blue_value"]) + """</p>
        <p>Clear: """ + str(system_state["clear_value"]) + """</p>
        <p><b>I2C devices:</b> """ + str(system_state["i2c_devices"]) + """</p>
    </div>

    <div class="card">
        <h2>System State</h2>
        <p><b>Pump:</b> """ + system_state["pump"] + """</p>
        <p><b>Fan:</b> """ + system_state["fan"] + """</p>
        <p><b>Relay:</b> """ + system_state["heat"] + """</p>
        <p><b>RGB LED:</b> """ + system_state["rgb"] + """</p>
    </div>

    <div class="card">
        <h2>Pump</h2>
        <a href="/pump/on"><button class="on">Pump ON</button></a>
        <a href="/pump/off"><button class="danger">Pump OFF</button></a>
    </div>

    <div class="card">
        <h2>Fan</h2>
        <a href="/fan/on"><button class="on">Fan ON</button></a>
        <a href="/fan/off"><button class="danger">Fan OFF</button></a>
    </div>

    <div class="card">
        <h2>Heating / Cooling Relay</h2>
        <a href="/heat/on"><button class="on">Relay ON</button></a>
        <a href="/heat/off"><button class="danger">Relay OFF</button></a>
    </div>

    <div class="card">
        <h2>RGB LED</h2>
        <a href="/rgb/red"><button>Red</button></a>
        <a href="/rgb/green"><button>Green</button></a>
        <a href="/rgb/blue"><button>Blue</button></a>
        <a href="/rgb/white"><button>White</button></a>
        <a href="/rgb/off"><button class="off">RGB OFF</button></a>
    </div>

    <div class="card">
        <a href="/"><button>Refresh</button></a>
    </div>
</body>
</html>"""

    return html

# =========================
# FAST RESPONSES
# =========================

def quick_redirect(conn):
    conn.send("HTTP/1.1 303 See Other\r\n")
    conn.send("Location: /\r\n")
    conn.send("Connection: close\r\n\r\n")

def send_page(conn):
    response = web_page()
    conn.send("HTTP/1.1 200 OK\r\n")
    conn.send("Content-Type: text/html\r\n")
    conn.send("Connection: close\r\n\r\n")
    conn.sendall(response)

def send_no_content(conn):
    conn.send("HTTP/1.1 204 No Content\r\n")
    conn.send("Connection: close\r\n\r\n")

# =========================
# WEB SERVER
# =========================

def start_server():
    ip = connect_wifi()

    if ip is None:
        return

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print("Web server running at http://" + ip)

    while True:
        conn = None

        try:
            maybe_update_sensors()

            conn, addr = s.accept()
            request = conn.recv(512)
            request = str(request)

            print("Request:", request)

            # Ignore browser favicon request
            if "/favicon.ico" in request:
                send_no_content(conn)
                conn.close()
                continue

            # Pump commands
            if "/pump/on" in request:
                pump_on()
                quick_redirect(conn)
                conn.close()
                continue

            if "/pump/off" in request:
                pump_off()
                quick_redirect(conn)
                conn.close()
                continue

            # Fan commands
            if "/fan/on" in request:
                fan_on()
                quick_redirect(conn)
                conn.close()
                continue

            if "/fan/off" in request:
                fan_off()
                quick_redirect(conn)
                conn.close()
                continue

            # Relay commands
            if "/heat/on" in request:
                heat_on()
                quick_redirect(conn)
                conn.close()
                continue

            if "/heat/off" in request:
                heat_off()
                quick_redirect(conn)
                conn.close()
                continue

            # RGB commands
            if "/rgb/red" in request:
                rgb_red()
                quick_redirect(conn)
                conn.close()
                continue

            if "/rgb/green" in request:
                rgb_green()
                quick_redirect(conn)
                conn.close()
                continue

            if "/rgb/blue" in request:
                rgb_blue()
                quick_redirect(conn)
                conn.close()
                continue

            if "/rgb/white" in request:
                rgb_white()
                quick_redirect(conn)
                conn.close()
                continue

            if "/rgb/off" in request:
                rgb_off()
                quick_redirect(conn)
                conn.close()
                continue

            # Normal page
            send_page(conn)
            conn.close()

        except Exception as e:
            print("Server error:", e)

            try:
                if conn:
                    conn.close()
            except:
                pass

# =========================
# START PROGRAM
# =========================

rgb_off()
update_sensors()
start_server()