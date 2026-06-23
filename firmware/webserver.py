# ============================================================
# DB4 web control server (interactive alternative to main.py).
# Serves a control dashboard over WiFi and exposes /data JSON.
#
# Reuses config.py + lib/ drivers, so there is no duplicated
# pin setup. WiFi credentials come from secrets.py.
# Run this OR main.py - not both (they share the same pins).
# ============================================================

import network
import socket
import utime
import json
import sys
from machine import Pin, I2C

import config
from thermistor import Thermistor
import actuators

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    raise ImportError("Create secrets.py from secrets_example.py with your WiFi details.")

TEMP_HYSTERESIS = 0.4

# ---- hardware -------------------------------------------------
thermistor = Thermistor()
cooling_pump = actuators.CoolingPump()
algae_pump = actuators.make_algae_pump()
waste_pump = actuators.make_waste_pump()
led = actuators.StatusLED()

oled = None
try:
    import ssd1306
    i2c = I2C(0, scl=Pin(config.I2C_SCL), sda=Pin(config.I2C_SDA), freq=config.I2C_FREQ)
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
except Exception as e:
    print("OLED disabled:", e)

# ---- state ----------------------------------------------------
start_ms = utime.ticks_ms()
last_oled_ms = 0

state = {
    "mode": "manual",
    "temperature": None,
    "raw_adc": 0,
    "target_temp": config.TARGET_TEMP,
    "cooling_pump": False,
    "cooling_pwm": 500,
    "algae_pump": False,
    "waste_pump": False,
    "uptime_s": 0,
}


# ---- control helpers -----------------------------------------
def update_led():
    if state["mode"] == "auto":
        led.blue()
    elif state["cooling_pump"]:
        led.green()
    elif state["algae_pump"] or state["waste_pump"]:
        led.red()
    else:
        led.off()


def cooling_on(pwm=None):
    cooling_pump.set(state["cooling_pwm"] if pwm is None else pwm)
    state["cooling_pwm"] = cooling_pump.duty
    state["cooling_pump"] = True


def cooling_off():
    cooling_pump.off()
    state["cooling_pump"] = False


def algae_on():
    algae_pump.on()
    state["algae_pump"] = True


def algae_off():
    algae_pump.off()
    state["algae_pump"] = False


def waste_on():
    waste_pump.on()
    state["waste_pump"] = True


def waste_off():
    waste_pump.off()
    state["waste_pump"] = False


def stop_all():
    cooling_off()
    algae_off()
    waste_off()
    state["mode"] = "manual"
    update_led()


def auto_control():
    temp = state["temperature"]
    if temp is None:
        cooling_off()
    elif temp > state["target_temp"] + TEMP_HYSTERESIS:
        cooling_on(state["cooling_pwm"])
    elif temp <= state["target_temp"]:
        cooling_off()


def update_oled():
    if oled is None:
        return
    try:
        oled.fill(0)
        oled.text("DB4 Web Server", 0, 0)
        t = state["temperature"]
        oled.text("Temp: ERROR" if t is None else "Temp: %.2f C" % t, 0, 14)
        oled.text("Mode: " + state["mode"], 0, 28)
        oled.text("CoolPump:%s" % ("ON" if state["cooling_pump"] else "OFF"), 0, 42)
        oled.text("A:%s W:%s" % (
            "ON" if state["algae_pump"] else "OFF",
            "ON" if state["waste_pump"] else "OFF"), 0, 54)
        oled.show()
    except Exception as e:
        print("OLED update failed:", e)


def update_system():
    global last_oled_ms
    raw, _, temp_c = thermistor.read(samples=10)
    state["raw_adc"] = 0 if raw is None else int(raw)
    state["temperature"] = None if temp_c is None else round(temp_c, 2)
    state["uptime_s"] = int(utime.ticks_diff(utime.ticks_ms(), start_ms) / 1000)

    if state["mode"] == "auto":
        auto_control()
    update_led()

    if utime.ticks_diff(utime.ticks_ms(), last_oled_ms) > 3000:
        update_oled()
        last_oled_ms = utime.ticks_ms()


# ---- WiFi -----------------------------------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 25
        while not wlan.isconnected() and timeout > 0:
            utime.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("WiFi connected. Open http://" + ip)
        return ip
    print("WiFi failed")
    return None


# ---- web page -------------------------------------------------
def web_page():
    return """<!DOCTYPE html>
<html>
<head>
    <title>DB4 Web Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; background:#111827; color:white; margin:0; padding:20px; }
        h1 { text-align:center; color:#60a5fa; }
        .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:15px; margin-top:20px; }
        .card { background:#1f2937; padding:18px; border-radius:12px; box-shadow:0 0 10px #00000055; }
        .value { font-size:30px; font-weight:bold; margin-top:10px; }
        .small { font-size:14px; color:#d1d5db; }
        button { width:100%; padding:14px; margin-top:8px; border:none; border-radius:8px; font-size:16px; font-weight:bold; cursor:pointer; }
        .on { background:#22c55e; color:white; }
        .off { background:#ef4444; color:white; }
        .blue { background:#3b82f6; color:white; }
        .yellow { background:#eab308; color:black; }
        .danger { background:#dc2626; color:white; font-size:20px; }
        input { width:100%; box-sizing:border-box; padding:12px; font-size:16px; border-radius:8px; border:none; margin-top:8px; }
        .status-on { color:#22c55e; }
        .status-off { color:#ef4444; }
    </style>
</head>
<body>
    <h1>DB4 Real-Time Control</h1>
    <div class="grid">
        <div class="card">
            <div class="small">Temperature</div>
            <div class="value" id="temperature">-- C</div>
            <div class="small">Raw ADC: <span id="raw_adc">--</span></div>
            <div class="small">Target: <span id="target_temp">--</span> C</div>
        </div>
        <div class="card">
            <div class="small">System Mode</div>
            <div class="value" id="mode">--</div>
            <button class="blue" onclick="sendCommand('/auto')">AUTO TEMP CONTROL</button>
            <button class="yellow" onclick="sendCommand('/manual')">MANUAL MODE</button>
        </div>
        <div class="card">
            <div class="small">Waste Pump</div>
            <div class="value" id="waste_pump">--</div>
            <button class="on" onclick="sendCommand('/waste_on')">Waste Pump ON</button>
            <button class="off" onclick="sendCommand('/waste_off')">Waste Pump OFF</button>
        </div>
        <div class="card">
            <div class="small">Cooling Pump</div>
            <div class="value" id="cooling_pump">--</div>
            <button class="on" onclick="sendCommand('/cooling_pump_on')">Cooling Pump ON</button>
            <button class="off" onclick="sendCommand('/cooling_pump_off')">Cooling Pump OFF</button>
        </div>
        <div class="card">
            <div class="small">Cooling Pump PWM</div>
            <div class="value" id="cooling_pwm">--</div>
            <input id="pwm_input" type="number" min="0" max="1023" value="500">
            <button class="blue" onclick="setPWM()">Set PWM</button>
        </div>
        <div class="card">
            <div class="small">Algae Pump</div>
            <div class="value" id="algae_pump">--</div>
            <button class="on" onclick="sendCommand('/algae_on')">Algae Pump ON</button>
            <button class="off" onclick="sendCommand('/algae_off')">Algae Pump OFF</button>
        </div>
        <div class="card">
            <div class="small">Safety</div>
            <button class="danger" onclick="sendCommand('/stop')">EMERGENCY STOP ALL</button>
            <div class="small" style="margin-top:12px;">Uptime: <span id="uptime">--</span> s</div>
        </div>
    </div>
<script>
function onOffText(v){ return v ? '<span class="status-on">ON</span>' : '<span class="status-off">OFF</span>'; }
function updateData(){
    fetch('/data').then(r=>r.json()).then(d=>{
        document.getElementById('temperature').innerHTML = d.temperature===null ? 'ERROR' : d.temperature+' C';
        document.getElementById('raw_adc').innerHTML = d.raw_adc;
        document.getElementById('target_temp').innerHTML = d.target_temp;
        document.getElementById('mode').innerHTML = d.mode;
        document.getElementById('cooling_pump').innerHTML = onOffText(d.cooling_pump);
        document.getElementById('cooling_pwm').innerHTML = d.cooling_pwm;
        document.getElementById('algae_pump').innerHTML = onOffText(d.algae_pump);
        document.getElementById('waste_pump').innerHTML = onOffText(d.waste_pump);
        document.getElementById('uptime').innerHTML = d.uptime_s;
    }).catch(e=>console.log("Update failed:", e));
}
function sendCommand(url){ fetch(url).then(r=>r.text()).then(_=>updateData()); }
function setPWM(){ sendCommand('/set_pwm?pwm=' + document.getElementById('pwm_input').value); }
setInterval(updateData, 1000);
updateData();
</script>
</body>
</html>
"""


# ---- HTTP helpers ---------------------------------------------
def send_response(client, content, content_type="text/html"):
    client.send("HTTP/1.1 200 OK\r\nContent-Type: %s\r\nConnection: close\r\n\r\n" % content_type)
    client.send(content if isinstance(content, (bytes, bytearray)) else content.encode())


def get_path(request):
    try:
        return request.split("\r\n")[0].split(" ")[1]
    except Exception:
        return "/"


def get_query_value(path, key):
    if "?" not in path:
        return None
    for part in path.split("?", 1)[1].split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k == key:
                return v
    return None


def set_pwm_from_path(path):
    value = get_query_value(path, "pwm")
    if value is None:
        return "NO PWM VALUE"
    try:
        pwm = max(0, min(config.PWM_MAX, int(value)))
    except ValueError:
        return "INVALID PWM VALUE"
    state["cooling_pwm"] = pwm
    if state["cooling_pump"]:
        cooling_on(pwm)
    return "PWM SET TO " + str(pwm)


# Routes that just need a mode switch + an action.
def _manual(action):
    state["mode"] = "manual"
    action()


def handle(path):
    if path == "/":
        return web_page(), "text/html"
    if path.startswith("/data"):
        return json.dumps(state), "application/json"
    if path.startswith("/auto"):
        state["mode"] = "auto"
        return "AUTO MODE", "text/html"
    if path.startswith("/manual"):
        state["mode"] = "manual"
        return "MANUAL MODE", "text/html"
    if path.startswith("/cooling_pump_on"):
        _manual(cooling_on); return "COOLING PUMP ON", "text/html"
    if path.startswith("/cooling_pump_off"):
        _manual(cooling_off); return "COOLING PUMP OFF", "text/html"
    if path.startswith("/algae_on"):
        _manual(algae_on); return "ALGAE PUMP ON", "text/html"
    if path.startswith("/algae_off"):
        _manual(algae_off); return "ALGAE PUMP OFF", "text/html"
    if path.startswith("/waste_on"):
        _manual(waste_on); return "WASTE PUMP ON", "text/html"
    if path.startswith("/waste_off"):
        _manual(waste_off); return "WASTE PUMP OFF", "text/html"
    if path.startswith("/set_pwm"):
        state["mode"] = "manual"
        return set_pwm_from_path(path), "text/html"
    if path.startswith("/stop"):
        stop_all(); return "ALL SYSTEMS STOPPED", "text/html"
    return "404 NOT FOUND", "text/html"


def start_web_server():
    ip = connect_wifi()
    if ip is None:
        print("Cannot start server without WiFi")
        return

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(1)
    server.settimeout(0.5)
    print("Web server running at http://" + ip)

    while True:
        update_system()
        client = None
        try:
            client, _ = server.accept()
            request = client.recv(1024).decode()
            path = get_path(request)
            content, ctype = handle(path)
            send_response(client, content, ctype)
        except OSError:
            pass
        except Exception as e:
            print("Server error:")
            sys.print_exception(e)
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass


def run():
    try:
        stop_all()
        start_web_server()
    except KeyboardInterrupt:
        print("Stopped by user")
        stop_all()
    except Exception as e:
        print("Fatal error:")
        sys.print_exception(e)
        stop_all()


if __name__ == "__main__":
    run()
