# DB4 Mussel Bioreactor — ESP32 (MicroPython)

Autonomous small-scale bioreactor that keeps mussels alive while controlling
temperature, feeding algae, transferring waste, and sensing algae concentration.
The ESP32 reads the sensors, runs the control logic, drives the pumps, and exposes
status over an OLED, an RGB LED, and an optional web dashboard.

This repo was reorganized into a clean module layout. All hardware details live in
one file (`firmware/config.py`); the rest of the code imports from it, so there is a
single source of truth for the pin map and pump polarity.

## Repository layout

```
db4/
├── firmware/              # everything that runs on the ESP32
│   ├── boot.py            # runs first on power-up: forces all actuators OFF
│   ├── main.py            # autonomous controller (PID + biological scheduler)
│   ├── webserver.py       # interactive web dashboard (alternative to main.py)
│   ├── stop.py            # manual emergency stop — sets every output OFF
│   ├── config.py          # pin map + all constants (single source of truth)
│   ├── secrets_example.py # copy to secrets.py and add your WiFi
│   └── lib/               # drivers (auto-on-path in MicroPython)
│       ├── thermistor.py  # 10k NTC temperature
│       ├── pid.py         # cooling PID controller
│       ├── actuators.py   # cooling pump, algae/waste pumps, RGB LED
│       ├── od_sensor.py   # TCS34725 optical density / algae estimate
│       ├── bio_model.py   # biological scheduler (algae feed + waste pump)
│       └── ssd1306.py     # OLED driver
├── tests/                 # standalone hardware bring-up tests
├── experiments/           # calibration scripts (OD, cooling, pump flow)
├── data/
│   ├── raw/               # raw OD / cooling / flow CSV datasets
│   ├── cleaned/           # cleaned CSV datasets
│   ├── plots/             # exported figures
│   └── aqua_lab/          # experiment analysis (xlsx, plots, notes)
└── tools/
    └── plot_od_data.py    # plots OD data from data/raw (run on your PC)
```

## ESP32 pin map

| ESP32 pin | Component | Notes |
|---|---|---|
| GPIO21 / GPIO22 | I2C SDA / SCL | shared by OLED + TCS34725 |
| GPIO35 | Thermistor (ADC) | replaces damaged GPIO34 — **do not use GPIO34** |
| GPIO18 / GPIO19 | Cooling pump IN1 / IN2 | L298N direction |
| GPIO32 | Cooling pump ENA | L298N PWM speed |
| GPIO23 | Algae pump | L9110S, ON/OFF |
| GPIO16 | Waste pump | see polarity note below |
| GPIO17 | Peltier / fan relay | optional |
| GPIO25 / GPIO26 / GPIO27 | RGB LED R / G / B | OD illumination + status |

Avoid GPIO12 (boot-strapping pin). GPIO34 is damaged.

### Pump polarity — verify on your board

The connections report lists GPIO16 as an L9110S input (active **high**), but the
tested code drove it as an **active-low relay** (`0 = ON`). The firmware keeps the
tested active-low behaviour by default. If the waste pump runs inverted, flip
`WASTE_PUMP_ON` / `WASTE_PUMP_OFF` in `config.py` — nothing else needs to change.
The same single-flag pattern is used for the algae pump and Peltier relay.

## Running it

Flash with VS Code + Pymakr (or `mpremote`/`ampy`). Upload the **contents of
`firmware/`** to the board root so `boot.py`, `main.py`, and `lib/` sit at `/`.

1. Copy `secrets_example.py` to `secrets.py` and fill in your WiFi (only needed for
   the web server). `secrets.py` is gitignored so credentials never get committed.
2. Upload `firmware/*` to the ESP32.
3. Reset the board. `boot.py` forces all actuators OFF, then MicroPython auto-runs
   `main.py` (autonomous control). To use the web dashboard instead, run
   `webserver.py` — they share the same pins, so run only one at a time.

`main.py` logs temperature, PWM, pump states, and the biological estimates to
`db4_final_log.csv` on the board.

## Control summary

- **Temperature:** cooling-only PID around 17.5 °C. Pump is forced off at/below
  17 °C (anti-freeze) and full-on above 18.3 °C. Peltier relay enabled while cooling.
- **Biological loop:** estimates algae/waste levels and doses the algae pump when the
  mussel tank runs low, then runs the waste pump after a delay. The two biological
  pumps never run at the same time.
- **Safety:** common ground across ESP32, drivers, and the 12 V supply; keep mains/
  12 V wiring away from water; test each pump separately before automatic mode.

## Notes from the cleanup

- `main.py` was a 700-line monolith with an inline PID and no OD sensing; it now
  imports the `pid.py` and `od_sensor.py` modules.
- WiFi credentials were hardcoded in the web server; they now live in `secrets.py`.
- The old `boot.py` ran an unsupervised pump self-test on every power-up — removed.
- Pin definitions were duplicated across files and inconsistent with the report;
  they are now centralized in `config.py`.
