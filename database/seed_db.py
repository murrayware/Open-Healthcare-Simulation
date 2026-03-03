# seed_hosps.py
# Generate 10 example hospitals with plausible values and write CSVs your importer expects.
# Optionally call: python hosps_csv_tool.py --import

from __future__ import annotations
import os, csv, random, math, subprocess, sys
from pathlib import Path

CSV_DIR = Path("hosps_csv")
random.seed(42)

HOSPITALS = [
    ("Riverside General",     "Edmonton"),
    ("North Valley Medical",  "Calgary"),
    ("Prairie Health Centre", "Red Deer"),
    ("Lakeside Regional",     "Lethbridge"),
    ("Foothills Community",   "Medicine Hat"),
    ("Meadowview Hospital",   "Grande Prairie"),
    ("Stony Creek Medical",   "Fort McMurray"),
    ("Aspen Ridge Hospital",  "Sherwood Park"),
    ("Maple Grove Medical",   "St. Albert"),
    ("Parkland General",      "Spruce Grove"),
]

def write_csv(path: Path, header: list[str], rows: list[list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def daily_curve24(base: float, peak_factor: float = 1.8, night_factor: float = 0.6) -> list[float]:
    """24h curve, scaled so mean ≈ base."""
    vals = []
    for h in range(24):
        theta = (h - 17) / 8.0
        bell = math.exp(-0.5 * theta * theta)
        day_weight = 0.4 + 0.6 * bell
        baseline = night_factor if h < 6 else 1.0
        vals.append(baseline * (1 + (peak_factor - 1) * day_weight))
    m = sum(vals) / 24.0
    return [round(base * v / m, 2) for v in vals]

def poissonish24(avg: float) -> list[float]:
    """24 values around avg with light randomness (for direct admits)."""
    sd = max(0.25, avg * 0.3)
    return [round(max(0.0, random.gauss(avg, sd)), 2) for _ in range(24)]

# ---- SERVICES (units + consults embedded) ----
def service_rows_for(hospital: str):
    """
    - Medicine: 24–40 beds, lognormal LOS mean 4.0–4.8 h (sigma 0.30–0.45)
      consult_p up to ~0.6; consult_admit_p up to ~0.95
    - Surgery:  10–20 beds, lognormal LOS mean 3.6–4.6 h
    - ICU:       6–16 beds, uniform LOS 24–120 h
    - Cardiology: 0 OR 10–14 beds, lognormal mean ~4.0 h
    """
    rows = []

    # Medicine
    med_beds = random.randint(24, 40)
    med_mean = round(random.uniform(4.0, 4.8), 2)
    med_sigma = round(random.uniform(0.30, 0.45), 2)
    rows.append([hospital, "Medicine", med_beds,
                 round(random.uniform(0.25, 0.60), 2),
                 round(random.uniform(0.55, 0.95), 2),
                 "lognormal", "", "", med_mean, med_sigma,
                 "uniform", 0.5, 1.5, "", "",
                 round(random.uniform(2.0, 5.0), 2)   # EIP mean hours
                 ])

    # Surgery
    surg_beds = random.randint(10, 20)
    surg_mean = round(random.uniform(3.6, 4.6), 2)
    surg_sigma = round(random.uniform(0.30, 0.45), 2)
    rows.append([hospital, "Cardiology", card_beds,
                 round(random.uniform(0.12, 0.25), 2),
                 round(random.uniform(0.40, 0.60), 2),
                 "lognormal", "", "", 4.0, 0.35,
                 "uniform", 0.5, 1.5, "", "",
                 round(random.uniform(1.5, 3.5), 2)
                 ])

    # ICU
    icu_beds = random.choice([6, 8, 10, 12, 14, 16])
    rows.append([hospital, "ICU", icu_beds,
                 round(random.uniform(0.05, 0.12), 2),
                 round(random.uniform(0.85, 0.95), 2),
                 "uniform", 24, 120, "", "",
                 "uniform", 0.75, 2.0, "", "",
                 round(random.uniform(0.25, 1.0), 2)
                 ])

    # Cardiology (sometimes an actual unit)
    if random.random() < 0.6:
        card_beds = random.randint(10, 14)
    else:
        card_beds = 0
    rows.append([hospital, "Cardiology", card_beds,
                 round(random.uniform(0.12, 0.25), 2),
                 round(random.uniform(0.40, 0.60), 2),
                 "lognormal", "", "", 4.0, 0.35,
                 "uniform", 0.5, 1.5, "", ""
                 ])
    return rows

# ---- DIRECT ADMITS (24h) ----
def directs_rows_for(hospital: str):
    """
    24h direct admits per service. Low hourly rates, sometimes disabled per service.
    """
    rows = []
    def svc_row(name: str, avg: float, enabled_prob: float):
        enabled = random.random() < enabled_prob
        arr = poissonish24(avg) if enabled else [0.0]*24
        rows.append([hospital, name, enabled, 24] + arr)

    svc_row("Medicine",  random.uniform(0.6, 2.5), 0.8)
    svc_row("Surgery",   random.uniform(0.3, 1.4), 0.7)
    svc_row("ICU",       random.uniform(0.08, 0.25), 0.6)
    # Cardiology rarely has direct admits unless it's a true unit with cath/obs:
    avg_card = 0.0 if random.random() < 0.5 else random.uniform(0.1, 0.6)
    svc_row("Cardiology", avg_card, 0.4)
    return rows

# ---- ARRIVALS (24h) ----
def arrivals_row_for(hospital: str):
    size_factor = random.uniform(0.8, 1.3)
    base = random.uniform(7, 14) * size_factor
    curve = daily_curve24(base, peak_factor=random.uniform(1.6, 2.0), night_factor=random.uniform(0.5, 0.7))
    lwbs_low, lwbs_high = random.randint(200, 320), random.randint(360, 500)   # 200–500 per your runner
    ft_p = round(random.uniform(0.45, 0.60), 2)
    admit_p = 0.25  # baseline per runner
    return [hospital, 24] + curve + [lwbs_low, lwbs_high, ft_p, admit_p]

# ---- EMS (24h) ----
def ems_row_for(hospital: str):
    base = random.uniform(1.0, 4.0)
    hourly = daily_curve24(base, peak_factor=random.uniform(1.4, 1.8), night_factor=random.uniform(0.7, 0.9))
    nurses = [max(1, int(round(x/3))) for x in hourly]  # heuristic scaling
    ctas = [0.04, 0.15, 0.48, 0.28, 0.05]
    pcrit = round(random.uniform(0.25, 0.35), 2)   # around 0.3
    pdtb  = round(random.uniform(0.45, 0.55), 2)   # around 0.5
    download_cap = random.choice([8, 10, 12])
    off_low, off_high = 5, 10
    crew_low, crew_high = 40, 50
    lwbs_low, lwbs_high = 45, 180
    ft_p = round(random.uniform(0.08, 0.15), 2)
    admit_p = round(random.uniform(0.55, 0.70), 2)

    row = [
        hospital, True, True, 24,
        *hourly,
        *ctas, pcrit, pdtb, download_cap,
        off_low, off_high,
        *nurses,
        crew_low, crew_high, lwbs_low, lwbs_high, ft_p, admit_p
    ]
    return row

# ---- AREAS ----
def areas_rows_for(hospital: str):
    beds_A = random.randint(10, 18)
    ratio = random.choice([1.5, 2, 2.5])
    return [[hospital, "A", beds_A, "ratio", ratio, True]]

# ---- DOCTORS ----
def doctors_rows_for(hospital: str):
    def hcaps(hi: int, lo: int):
        base = [hi, hi, hi, hi, hi-1, hi-1, lo, lo, lo, lo, lo, lo]
        return [max(lo, b) for b in base]

    return [
        [hospital, "DrA1",  "A",    0,   12*60, random.choice([10, 11, 12]), *hcaps(3,2), "uniform", 12,35, 8,20],
        [hospital, "DrA2",  "A",  12*60, 12*60, random.choice([10, 11, 12]), *hcaps(3,2), "uniform", 12,35, 8,20],
        [hospital, "DrFT1", "FAST", 0,   12*60, 22, *hcaps(8,4), "uniform", 5,12, 3,8],
        [hospital, "DrFT2", "FAST",12*60,12*60, 22, *hcaps(8,4), "uniform", 5,12, 3,8],
    ]

# ---- ORDERS ----
def orders_row_for(hospital: str):
    proc_prob = round(random.uniform(0.20, 0.30), 2)
    lab_prob  = round(random.uniform(0.45, 0.60), 2)
    di_prob   = round(random.uniform(0.30, 0.40), 2)
    p_one     = round(random.uniform(0.20, 0.30), 2)
    p_three   = round(random.uniform(0.08, 0.15), 2)
    return [
        hospital,
        proc_prob, lab_prob, di_prob,
        2, 6, 10, 40,   # proc work, time
        2, 5, 45, 120,  # lab work, time
        1, 4,           # di work
        30, 90, 60, 150, 45, 120,  # Xray, CT, US
        p_one, p_three
    ]

def disposition_row_for(hospital: str):
    return [hospital, 20, 90, 45, 240]

def capabilities_row_for(hospital: str):
    return [
        hospital,
        random.choice([True, True, True, False]),  # has_xray
        random.choice([False, False, True]),       # has_ct (mostly False)
        random.choice([True, True, False]),        # has_us
        False, True,                                # transfer_only_admit, external_di_roundtrip
        90, 180, 90, 180
    ]

def fasttrack_row_for(hospital: str):
    return [hospital, True, "FAST", random.randint(16, 24), round(random.uniform(0.45, 0.60), 2)]

def main(write_only: bool = False, run_import: bool = False):
    # hospitals.csv
    write_csv(CSV_DIR/"hospitals.csv", ["hospital","city"], HOSPITALS)

    # services.csv
    svc_rows = []
    for h, _ in HOSPITALS:
        svc_rows += service_rows_for(h)
    write_csv(
        CSV_DIR/"services.csv",
        ["hospital","service_name","bed_base",
         "p_consult","p_admit",
         "los_time_type","los_hours_low","los_hours_high","los_hours_mean","los_hours_sigma",
         "consult_time_type","consult_hours_low","consult_hours_high","consult_hours_mean","consult_hours_sigma",'eip_mean_hours'],
        svc_rows
    )

    # direct_admits.csv
    da_rows = []
    for h, _ in HOSPITALS:
        da_rows += directs_rows_for(h)
    write_csv(
        CSV_DIR/"direct_admits.csv",
        ["hospital","service_name","enabled","hours"] + [f"da_{i}" for i in range(24)],
        da_rows
    )

    # arrivals.csv
    arr_rows = [arrivals_row_for(h) for h, _ in HOSPITALS]
    write_csv(
        CSV_DIR/"arrivals.csv",
        ["hospital","hours"] + [f"walkin_{i}" for i in range(24)] + ["lwbs_low","lwbs_high","fasttrack_p","admit_p"],
        arr_rows
    )

    # ems.csv (crew_low/crew_high)
    ems_rows = [ems_row_for(h) for h, _ in HOSPITALS]
    ems_header = ["hospital","enabled","internal_generation","hours"] + \
                 [f"hourly_{i}" for i in range(24)] + \
                 ["ctas1","ctas2","ctas3","ctas4","ctas5","p_critical","p_direct_to_bed","download_capacity",
                  "offload_low","offload_high"] + \
                 [f"nurses_{i}" for i in range(24)] + \
                 ["crew_low","crew_high","lwbs_low","lwbs_high","fasttrack_p","admit_p"]
    write_csv(CSV_DIR/"ems.csv", ems_header, ems_rows)

    # areas.csv
    areas_rows = []
    for h, _ in HOSPITALS:
        areas_rows += areas_rows_for(h)
    write_csv(
        CSV_DIR/"areas.csv",
        ["hospital","area_name","beds","nurse_model","nurse_ratio","lab_support"],
        areas_rows
    )

    # doctors.csv
    docs_rows = []
    for h, _ in HOSPITALS:
        docs_rows += doctors_rows_for(h)
    doc_header = ["hospital","name","area","start_minute","shift_minutes","max_active_panel"] + \
                 [f"hcap_{i}" for i in range(1,13)] + \
                 ["assess_type","assess_low","assess_high","reassess_low","reassess_high"]
    write_csv(CSV_DIR/"doctors.csv", doc_header, docs_rows)

    # orders.csv (with p_one_touch, p_three_touch)
    write_csv(
        CSV_DIR/"orders.csv",
        ["hospital","proc_prob","lab_prob","di_prob",
         "proc_work_low","proc_work_high","proc_time_low","proc_time_high",
         "lab_work_low","lab_work_high","lab_time_low","lab_time_high",
         "di_work_low","di_work_high",
         "xray_low","xray_high","ct_low","ct_high","us_low","us_high",
         "p_one_touch","p_three_touch"],
        [orders_row_for(h) for h, _ in HOSPITALS]
    )

    # disposition.csv
    write_csv(
        CSV_DIR/"disposition.csv",
        ["hospital","stabil_low","stabil_high","post_low","post_high"],
        [disposition_row_for(h) for h, _ in HOSPITALS]
    )

    # capabilities.csv
    write_csv(
        CSV_DIR/"capabilities.csv",
        ["hospital","has_xray","has_ct","has_us","transfer_only_admit","external_di_roundtrip",
         "ext_di_low","ext_di_high","admit_transfer_low","admit_transfer_high"],
        [capabilities_row_for(h) for h, _ in HOSPITALS]
    )

    # fasttrack.csv
    write_csv(
        CSV_DIR/"fasttrack.csv",
        ["hospital","enabled","name","assessment_spaces","route_probability"],
        [fasttrack_row_for(h) for h, _ in HOSPITALS]
    )

    print(f"✅ Wrote seed CSVs for {len(HOSPITALS)} hospitals under {CSV_DIR}/")

    if run_import:
        cmd = [sys.executable, "hosps_csv_tool.py", "--import", "--dir", str(CSV_DIR)]
        print("→ Running importer:", " ".join(cmd))
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    # usage:
    #   python seed_hosps.py          # just write CSVs
    #   python seed_hosps.py import   # write CSVs and run the importer
    do_import = len(sys.argv) > 1 and sys.argv[1].lower().startswith("import")
    main(run_import=do_import)
