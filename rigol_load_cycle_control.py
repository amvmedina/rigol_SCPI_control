import pyvisa, csv, time
from datetime import datetime

# -------- USER SETTINGS --------
I_SET = 1.0                 # A (keep constant across cycles)
T_ON = 30.0                 # s  load ON per pulse
T_REST = 60.0               # s  rest/OCV after each pulse
SAMPLE_DT = 0.5             # s  logging period
OCV_CUTOFF = 3.00           # V  stop when OCV after rest <= this
V_MIN_ON = 2.80             # V  safety: abort pulse if loaded V < this
MAX_CYCLES = 999            # safety cap
CSV_FILE = "dl3021_pulse_log.csv"
ADDRESS = None              # None = first VISA resource

# -------- VISA CONNECT --------
rm = pyvisa.ResourceManager('@py')
addr = ADDRESS or rm.list_resources()[0]
dl = rm.open_resource(addr); dl.timeout = 5000
print("Connected:", dl.query("*IDN?").strip())

# -------- PREP INSTRUMENT --------
dl.write("*RST"); dl.write(":SYST:REM")
dl.write(":FUNC CURR")
dl.write(f":CURR {I_SET}")
dl.write(":INP OFF")

# -------- HELPERS --------
def meas_all():
    v = float(dl.query(":MEAS:VOLT?"))
    i = float(dl.query(":MEAS:CURR?"))
    cap = float(dl.query(":MEAS:CAP?"))
    en  = float(dl.query(":MEAS:ENER?"))
    return v, i, cap, en

# -------- LOG HEADER --------
fields = ["timestamp","cycle","phase","elapsed_s","V","I","mAh","Wh"]
f = open(CSV_FILE,"w",newline=""); w = csv.writer(f); w.writerow(fields)

def log(cycle, phase, t, v, i, cap, en):
    w.writerow([datetime.now().isoformat(), cycle, phase, f"{t:.1f}", v, i, cap, en])
    print(f"{cycle:03d} {phase:7s} {t:6.1f}s | {v:7.4f} V | {i:6.3f} A | {cap:7.3f} mAh | {en:7.4f} Wh")

# -------- MAIN LOOP --------
cycle = 0
try:
    while cycle < MAX_CYCLES:
        cycle += 1
        # ---- LOAD ON (discharge pulse) ----
        dl.write(":INP ON")
        t0 = time.time()
        print(f"\n=== CYCLE {cycle} : LOAD ON ({I_SET} A for {T_ON}s) ===")
        while True:
            t = time.time() - t0
            v,i,cap,en = meas_all()
            log(cycle, "LOAD_ON", t, v, i, cap, en)
            if v <= V_MIN_ON:                     # safety cutoff under load
                print(">> Loaded voltage below safety limit, aborting pulse.")
                break
            if t >= T_ON:
                break
            time.sleep(SAMPLE_DT)

        # ---- LOAD OFF (rest / rebound) ----
        dl.write(":INP OFF")
        t0 = time.time()
        print(f"=== CYCLE {cycle} : REST ({T_REST}s) ===")
        while True:
            t = time.time() - t0
            v,i,cap,en = meas_all()
            log(cycle, "REST", t, v, i, cap, en)
            if t >= T_REST:
                ocv = v  # OCV at end of rest
                break
            time.sleep(SAMPLE_DT)

        # ---- STOP CRITERIA ----
        if ocv <= OCV_CUTOFF:
            print(f"\n>>> STOP: OCV after rest = {ocv:.3f} V ≤ {OCV_CUTOFF:.3f} V")
            break

    print(f"\nDone. Data saved to {CSV_FILE}")

finally:
    dl.write(":INP OFF")
    dl.close()
    f.close()
