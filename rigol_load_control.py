import pyvisa
import csv
import time
from datetime import datetime

# ==============================
# USER SETTINGS
# ==============================
CURRENT_SET = 1.0        # Amperes
LOAD_TIME = 30           # seconds with load ON
REBOUND_TIME = 60        # seconds measuring after load OFF
SAMPLE_PERIOD = 0.5      # seconds between readings
CSV_FILE = "dl3021_log.csv"
ADDRESS = None           # auto-detect if None

# ==============================
# CONNECT TO INSTRUMENT
# ==============================
rm = pyvisa.ResourceManager('@py')
devices = rm.list_resources()
if not devices:
    raise RuntimeError("No VISA instruments found. Check USB/LAN connection.")
if ADDRESS is None:
    ADDRESS = devices[0]

dl = rm.open_resource(ADDRESS)
dl.timeout = 5000
print("Connected to:", dl.query("*IDN?").strip())

# ==============================
# INITIAL SETUP
# ==============================
dl.write("*RST")          # optional: reset to known state
dl.write(":SYST:REM")     # remote control
dl.write(":FUNC CURR")    # constant current mode
dl.write(f":CURR {CURRENT_SET}")
dl.write(":INP OFF")      # make sure load starts OFF

# ==============================
# LOGGING FUNCTION
# ==============================
def read_measurements(t):
    """Read all key measurements and return as a list"""
    v = float(dl.query(":MEAS:VOLT?"))
    i = float(dl.query(":MEAS:CURR?"))
    cap = float(dl.query(":MEAS:CAP?"))
    en = float(dl.query(":MEAS:ENER?"))
    return [datetime.now().isoformat(), f"{t:.1f}", v, i, cap, en]

# ==============================
# DATA LOGGING
# ==============================
fields = ["Timestamp", "Elapsed_s", "Voltage_V", "Current_A", "Capacity_mAh", "Energy_Wh"]

with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(fields)

    start = time.time()
    phase = "LOAD"
    dl.write(":INP ON")   # start load
    print("\n=== LOAD PHASE STARTED ===")

    while True:
        t = time.time() - start

        # During load phase
        if phase == "LOAD" and t >= LOAD_TIME:
            dl.write(":INP OFF")
            phase = "REBOUND"
            print("\n=== LOAD PHASE ENDED → REBOUND PHASE STARTED ===")

        # During rebound phase
        if phase == "REBOUND" and t >= LOAD_TIME + REBOUND_TIME:
            break

        # Record measurements
        data = read_measurements(t)
        writer.writerow(data)
        print(f"{t:6.1f}s | {data[2]:7.4f} V | {data[3]:6.3f} A | {data[4]:7.3f} mAh | {data[5]:7.4f} Wh")

        time.sleep(SAMPLE_PERIOD)

print("\n=== TEST COMPLETE ===")
print(f"Data saved to: {CSV_FILE}")

dl.close()
