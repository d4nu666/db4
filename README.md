# DB4 Mussel Bioreactor — ESP32 (MicroPython)

Autonomous small-scale bioreactor that keeps mussels alive while regulating water
temperature, feeding algae, transferring waste, and measuring algae concentration.
The ESP32 reads the sensors, runs the control logic, drives the pumps, shows status
on an OLED and RGB LED, and serves a live web dashboard.

It is designed to **run constantly**: once powered, it controls and logs on its own,
recovers from transient faults, and never needs a computer attached.

All hardware details live in one file (`firmware/config.py`); every other module
imports from it, so there is a single source of truth for the pin map and polarity.

## Repository layout

```
db4/
├── firmware/                  # everything that runs on the ESP32
│   ├── boot.py                # runs first on power-up: forces all actuators OFF
│   ├── main.py                # entry point: control loop + launches the dashboard
│   ├── webserver.py           # web dashboard + CSV download (run on a thread)
│   ├── web_server_threaded.py # experimental message-based server (|type|msg|)
│   ├── stop.py                # manual emergency stop — sets every output OFF
│   ├── config.py              # pin map + all constants (single source of truth)
│   ├── secrets_example.py     # copy to secrets.py and add your WiFi
│   └── lib/                   # drivers (MicroPython auto-adds /lib to the path)
│       ├── system.py          # shared hardware + state (single control authority)
│       ├── thermistor.py      # 10k NTC temperature
│       ├── actuators.py       # cooling pump, algae/waste pumps, RGB LED
│       ├── od_sensor.py       # TCS34725 optical density -> algae cells/mL
│       ├── bio_model.py        # biological scheduler (algae feed + waste pump)
│       ├── pid.py             # PID class (kept for reference; not used by default)
│       └── ssd1306.py         # OLED driver
├── tests/                     # standalone hardware bring-up tests
├── experiments/               # calibration scripts (OD, cooling, pump flow)
├── data/                      # datasets, plots and analysis
└── tools/
    └── plot_od_data.py        # plots OD data from data/raw (run on your PC)
```

## ESP32 pin map

| ESP32 pin | Component | Notes |
|---|---|---|
| GPIO21 / GPIO22 | I2C SDA / SCL | shared by OLED + TCS34725 OD sensor |
| GPIO35 | Thermistor (ADC) | 10k NTC; replaces damaged GPIO34 |
| GPIO32 | Cooling pump | L298N, **PWM only** — no IN1/IN2 direction pins |
| GPIO23 | Algae pump | L9110S, ON/OFF |
| GPIO19 | Waste pump | L9110S, ON/OFF |
| GPIO16 | Relay (Peltier / cooling) | active LOW |
| GPIO27 / GPIO26 / GPIO25 | RGB LED R / G / B | OD illumination + status |

Do **not** use GPIO34 (damaged) or GPIO12 (boot-strapping pin).

### Pump / relay polarity — verify on your board

Pump and relay polarity is centralised in `config.py`. If a pump or the Peltier
relay runs inverted on your hardware, swap its `*_ON` / `*_OFF` pair
(`ALGAE_PUMP_ON`/`OFF`, `WASTE_PUMP_ON`/`OFF`, `PELTIER_ON`/`OFF`) — nothing else
changes. Defaults follow the tested wiring (relay active-low, `0 = ON`).

## Temperature control (hysteresis, 17–18 °C)

Cooling is simple on/off (bang-bang) control that holds the tank between
`LOW_TEMP_LIMIT` (17 °C) and `HIGH_TEMP_LIMIT` (18 °C):

- **≥ 18 °C (too hot)** → Peltier relay **and** cooling pump turn fully ON.
- **≤ 17 °C (too cold)** → Peltier and pump turn OFF.
- **in between** → the current state is held, so it does not rapidly switch.
- **sensor failure** → everything is switched OFF (fail-safe).

(`lib/pid.py` keeps a PID controller for reference, but the active strategy is the
hysteresis controller in `lib/system.py`.)

## Algae concentration (OD sensing)

The TCS34725 optical-density sensor is read every `OD_SAMPLE_INTERVAL` seconds
(default 30 s, briefly using the white RGB LED for illumination). The reading is
converted to **cells/mL** and shown on the dashboard and written to the log. If the
sensor is not connected it degrades gracefully to `n/a`. The cells/mL value relies on
the single-point calibration in `od_sensor.AlgaeODModel` — calibrate it for accuracy.

## Biological feeding loop

The scheduler estimates algae/waste levels and doses the **algae pump** when the
mussel tank runs low, then runs the **waste pump** after a delay. The two biological
pumps never run at the same time. Timings and thresholds are in `config.py`.

## Runs constantly

- `main.py` loops **forever** (`RUN_TIME_SECONDS = 0`). Set a positive value only to
  stop after a fixed time.
- Each loop iteration is guarded, so a transient fault prints a warning and the
  bioreactor keeps running; if the whole program ever crashes it auto-restarts.
- A hardware **watchdog** reboots the board if the loop ever hangs (`USE_WATCHDOG`,
  60 s). Set `USE_WATCHDOG = False` while debugging at the serial REPL.

## Data logging & download

Every sample is written to a numbered CSV on the board: `db4_log_001.csv`,
`db4_log_002.csv`, … (a new file each boot, so runs are never overwritten). To keep
running constantly without filling the flash, a file rolls over to the next number
after `MAX_LOG_ROWS` samples (~11 h), and only the newest `MAX_LOG_FILES` (10) are
kept — older ones auto-delete.

Each row logs: time, mode, temperature, target, cooling PWM, algae/waste pump and
Peltier states, algae OD + cells/mL, and the biological estimates (Am, Aa, Wm, Wa).

On the dashboard, **Download current run** saves the active CSV, and **All saved
runs** lists every log with a download link.

## Web dashboard

`main.py` starts `webserver.py` on a background thread, so control and the dashboard
run together on one shared set of hardware (`lib/system.py`) — they never fight over
the pins. The page shows live temperature, algae concentration, pump and Peltier
states, mode and uptime, and offers:

- **Auto / Manual** — Auto lets the autonomous controller own the actuators; Manual
  (or pressing any pump button) pauses it so your manual commands stick.
- Manual **pump on/off** and **cooling PWM** controls.
- **Emergency Stop** — always works; forces everything off.
- **Download** the current run or any past run as CSV.

`webserver.py` can also be run on its own; it then starts in manual mode.

## Running it

Flash with VS Code + Pymakr (or `mpremote` / `ampy`).

1. Copy `secrets_example.py` to `secrets.py` and fill in your WiFi (needed for the
   dashboard). `secrets.py` is gitignored, so it is never committed — but it **must**
   be uploaded to the board.
2. Upload the **contents of `firmware/`** to the board **root** (`/`), so that
   `boot.py`, `main.py`, `config.py`, `secrets.py` and the `lib/` folder all sit at
   the top level. (MicroPython only auto-runs `/boot.py` and `/main.py` — files left
   inside a `/firmware` folder on the board will not start.)
3. Power-cycle the ESP32. `boot.py` forces all actuators OFF, then `main.py` starts
   the dashboard thread and the control loop. If WiFi / `secrets.py` is missing, the
   control loop still runs and the dashboard is simply skipped.

Find the dashboard IP from your router (or the serial output) and open
`http://<that-ip>` on the same network.

## Safety

- Share a common ground across the ESP32, all drivers, and the 12 V supply.
- Keep the 12 V supply, relay terminals and Peltier wiring away from water.
- Test each pump, the relay, the thermistor, the OLED, the OD sensor and the LED
  separately before enabling automatic mode.
