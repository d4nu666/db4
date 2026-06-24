# ============================================================
# DB4 web control dashboard.
#
# Serves a control page over WiFi and exposes /data JSON. Operates
# on the shared hardware/state in system.py, so it never fights
# main.py over the pins.
#
# Normally started by main.py on a background thread (serve()).
# Can also be run standalone, in which case it refreshes the
# sensors itself and starts in manual mode.
#
# WiFi credentials come from secrets.py.
# ============================================================

import network
import socket
import time
import json
import sys
import os

# Import path fix - works whether files are at / or /firmware.
try:
    os.chdir("/firmware")
except OSError:
    pass
for _p in ["/", "/lib", "/firmware", "/firmware/lib"]:
    if _p not in sys.path:
        sys.path.append(_p)

import config
import system

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    raise ImportError("Create secrets.py from secrets_example.py with your WiFi details.")


# ---- WiFi -----------------------------------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 25
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
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
    system.state["cooling_pwm"] = pwm
    if system.state["cooling_pump"]:
        system.cooling_set(pwm)
    return "PWM SET TO " + str(pwm)


# A manual command first switches the system into manual mode so the
# autonomous loop in main.py stops overriding the actuators.
def _manual(action):
    system.set_mode("manual")
    action()


def handle(path):
    if path == "/":
        return web_page(), "text/html"
    if path.startswith("/data"):
        return json.dumps(system.state), "application/json"
    if path.startswith("/auto"):
        system.set_mode("auto")
        return "AUTO MODE", "text/html"
    if path.startswith("/manual"):
        system.set_mode("manual")
        return "MANUAL MODE", "text/html"
    if path.startswith("/cooling_pump_on"):
        _manual(lambda: system.cooling_set(system.state["cooling_pwm"]))
        return "COOLING PUMP ON", "text/html"
    if path.startswith("/cooling_pump_off"):
        _manual(system.cooling_off); return "COOLING PUMP OFF", "text/html"
    if path.startswith("/algae_on"):
        _manual(system.algae_on); return "ALGAE PUMP ON", "text/html"
    if path.startswith("/algae_off"):
        _manual(system.algae_off); return "ALGAE PUMP OFF", "text/html"
    if path.startswith("/waste_on"):
        _manual(system.waste_on); return "WASTE PUMP ON", "text/html"
    if path.startswith("/waste_off"):
        _manual(system.waste_off); return "WASTE PUMP OFF", "text/html"
    if path.startswith("/set_pwm"):
        system.set_mode("manual")
        return set_pwm_from_path(path), "text/html"
    if path.startswith("/stop"):
        system.emergency_stop(); return "ALL SYSTEMS STOPPED", "text/html"
    return "404 NOT FOUND", "text/html"


def serve():
    """Blocking web-server loop. Started on a thread by main.py."""
    ip = connect_wifi()
    if ip is None:
        print("Web dashboard unavailable (no WiFi)")
        return

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(1)
    server.settimeout(0.5)
    print("Web dashboard running at http://" + ip)

    while True:
        client = None
        try:
            client, _ = server.accept()
            request = client.recv(1024).decode()
            path = get_path(request)
            content, ctype = handle(path)
            send_response(client, content, ctype)
        except OSError:
            pass  # accept() timeout - lets the loop breathe
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
    """Standalone entry: refresh sensors in the background, then serve."""
    system.set_mode("manual")
    try:
        import _thread

        def _refresh():
            while True:
                try:
                    system.read_and_update()
                except Exception as e:
                    print("refresh error:", e)
                time.sleep(2)

        _thread.start_new_thread(_refresh, ())
    except Exception as e:
        print("sensor refresh not started:", e)
    serve()


if __name__ == "__main__":
    run()
