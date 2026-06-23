# ============================================================
# DB4 Mussel Bioreactor - central configuration
# Single source of truth for pins, polarity and constants.
# Pin map follows the ESP32 connections report (June 2026).
#
# If a pump or relay runs inverted on your board, flip the
# matching *_ON / *_OFF or *_ACTIVE_HIGH value here only.
# ============================================================

# ---- I2C bus (OLED SSD1306 + TCS34725 OD sensor) ----
I2C_SDA = 21
I2C_SCL = 22
I2C_FREQ = 400000

# ---- Thermistor (10k NTC, voltage divider) ----
# GPIO34 is damaged - do not use it. GPIO35 replaces it.
THERMISTOR_PIN = 35
SERIES_RESISTOR = 10000      # Rs  (ohm)
NOMINAL_RESISTANCE = 10000   # R0  (ohm)
NOMINAL_TEMPERATURE = 25.0   # T0  (degC)
BETA = 3950                  # beta coefficient
ADC_MAX = 4095               # 12-bit ADC

# ---- Cooling pump on L298N (PWM) ----
COOL_IN1_PIN = 18
COOL_IN2_PIN = 19
COOL_PWM_PIN = 32
COOL_PWM_FREQ = 1000
PWM_MAX = 1023

# ---- Algae pump on L9110S (single input, ON/OFF, active HIGH) ----
ALGAE_PUMP_PIN = 23
ALGAE_PUMP_ON = 1
ALGAE_PUMP_OFF = 0

# ---- Waste pump on GPIO16 ----
# NOTE: the connections report lists GPIO16 as an L9110S input
# (active HIGH), but the tested code drives it as an ACTIVE-LOW
# relay. The tested behaviour is kept as default. If the waste
# pump logic is reversed on your board, swap these two values.
WASTE_PUMP_PIN = 16
WASTE_PUMP_ON = 0            # active-low relay: 0 = ON
WASTE_PUMP_OFF = 1

# ---- Peltier / fan relay (optional, active LOW) ----
PELTIER_RELAY_PIN = 17
PELTIER_ON = 0
PELTIER_OFF = 1

# ---- RGB LED (HW-479 / KY-016) - OD illumination + status ----
LED_R_PIN = 25
LED_G_PIN = 26
LED_B_PIN = 27

# ============================================================
# Temperature control
# ============================================================
TARGET_TEMP = 17.5           # setpoint (degC)
LOW_TEMP_LIMIT = 17.0        # below this: stop cooling (anti-freeze)
HIGH_TEMP_LIMIT = 18.0       # above this: status warning
PUMP_FORCE_OFF_TEMP = 17.0   # hard cutoff for the cooling pump
PUMP_FULL_ON_TEMP = 18.3     # full-speed cooling above this

# PID gains (cooling-only). Output is 0..100 %, mapped to PWM.
PID_KP = 180.0
PID_KI = 0.05
PID_KD = 250.0
PID_INTEGRAL_LIMIT = 200.0

MIN_COOLING_PWM = 450        # below this the pump stalls
MAX_COOLING_PWM = PWM_MAX

# ============================================================
# Biological model (control-oriented, see report section 5)
# Am/Aa = algae level in mussel/algae tank
# Wm/Wa = waste level in mussel/algae tank
# ============================================================
KF = 0.35          # mussel filtration coefficient (h^-1)
MU = 0.0351        # algae natural growth rate (h^-1)
WASTE_YIELD = 0.60 # waste produced per algae consumed
ETA = 0.03         # nutrient effect on algae growth
ALPHA_A = 80.0     # algae pump transfer strength (h^-1)
ALPHA_W = 100.0    # waste pump transfer strength (h^-1)

A_LOW = 0.45       # start feeding below this algae level
W_MAX = 0.22       # start waste pump above this waste level

# Dose durations (s)
ALGAE_FEED_DURATION = 20
WASTE_PUMP_DURATION = 15

# Safety timing (s)
MIN_TIME_BETWEEN_ALGAE_FEEDS = 45 * 60
MAX_TIME_BETWEEN_ALGAE_FEEDS = 2 * 60 * 60
MIN_WASTE_DELAY_AFTER_FEED = 30 * 60
MAX_WASTE_DELAY_AFTER_FEED = 75 * 60
MIN_TIME_BETWEEN_WASTE_PUMPS = 45 * 60

# Initial estimated biological state (start low so it feeds early)
INIT_AM = 0.40
INIT_AA = 1.00
INIT_WM = 0.00
INIT_WA = 0.00

# ============================================================
# Run / logging
# ============================================================
RUN_TIME_SECONDS = 6 * 60 * 60
SAMPLE_TIME = 2
LOG_FILE = "db4_final_log.csv"
