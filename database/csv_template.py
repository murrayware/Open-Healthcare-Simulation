# hosps_csv_tool.py
# Recreates SQLite db.db, writes CSV templates seeded to match your runner,
# and imports them into a single-table JSON-per-config layout.
#
# Key changes vs prior:
# • Consult fields embedded inside each unit (units[svc].consult_*)
# • Arrivals/EMS are 24h (0..23)
# • Orders include p_one_touch, p_three_touch
# • EMS crew_hospital_time_dist is UNIFORM (crew_low, crew_high)
# • Direct admits file supports hours=12 or 24 (0..hours-1); you can leave disabled

from __future__ import annotations
import argparse, csv, json, os, sys
from collections import defaultdict
from typing import Any, Dict, List

# ---------- SQLAlchemy model ----------
from sqlalchemy import create_engine, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.types import TypeDecorator

DB_FILE = os.path.join(os.path.dirname(__file__), "db.db")
DB_URL  = f"sqlite:///{DB_FILE}"
CSV_DIR = os.path.join(os.path.dirname(__file__), "hosps_csv")

class JSON(TypeDecorator):
    """SQLite-friendly JSON stored as TEXT."""
    impl = Text
    cache_ok = True
    def process_bind_param(self, value, dialect):
        return None if value is None else json.dumps(value)
    def process_result_value(self, value, dialect):
        return None if value is None else json.loads(value)

class Base(DeclarativeBase):
    pass

class DefaultHosp(Base):
    __tablename__ = "default_hosps"
    id:   Mapped[int]  = mapped_column(Integer, primary_key=True)
    name: Mapped[str]  = mapped_column(String, unique=True, nullable=False)
    city: Mapped[str]  = mapped_column(String, nullable=True)

    inpatient_cfg:   Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    areas:           Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    doctors:         Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    arrivals:        Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ems:             Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    triage_weights:  Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    orders:          Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    consults:        Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # mirror for legacy
    disposition:     Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    capabilities:    Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    fasttrack:       Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

engine = create_engine(DB_URL, echo=False, future=True)

# ---------- helpers ----------
def Bool(x):  return str(x).strip().lower() in ("1","true","t","yes","y")
def Int(x):   return None if str(x).strip()=="" else int(float(x))
def Float(x): return None if str(x).strip()=="" else float(x)

def takeN(prefix: str, row: dict, n: int) -> List[float]:
    return [Float(row.get(f"{prefix}{i}", "") or 0) for i in range(n)]

def take_seq_1_based(prefix: str, row: dict, n: int) -> List[int]:
    return [Int(row.get(f"{prefix}{i}", "") or 0) for i in range(1, n+1)]

def write_csv(path: str, header: List[str], rows: List[List[Any]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def load_csv(path: str) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ---------- write CSV templates (seeded to your runner) ----------
def write_templates(outdir: str = CSV_DIR):
    # hospitals
    write_csv(f"{outdir}/hospitals.csv", ["hospital","city"], [["Sample General","Edmonton"]])

    # services: units + embedded consult fields (LOS/consult in HOURS here)
    write_csv(
        f"{outdir}/services.csv",
        ["hospital","service_name","bed_base",
     "p_consult","p_admit",
     "los_time_type","los_hours_low","los_hours_high","los_hours_mean","los_hours_sigma",
     "consult_time_type","consult_hours_low","consult_hours_high","consult_hours_mean","consult_hours_sigma",
     "eip_mean_hours"],
        [
            # Medicine (matches runner: beds=32, lognormal mean=4.4h, sigma=0.35; consult 0.6/0.95, consult time 0.5–1.5h)
            ["Sample General","Medicine",32, 0.60,0.95, "lognormal","","",4.4,0.35, "uniform",0.5,1.5,"",""],
            # Surgery (beds=12, lognormal mean=4.1h, sigma=0.40; consult 0.18/0.70; consult time 0.5–1.25h)
            ["Sample General","Surgery",12,  0.18,0.70, "lognormal","","",4.1,0.40, "uniform",0.5,1.25,"",""],
            # ICU (beds=8, LOS uniform 24–120h; consult 0.08/0.90; consult time 0.75–2.0h)
            ["Sample General","ICU",8,        0.08,0.90, "uniform",24,120,"","",   "uniform",0.75,2.0,"",""],
            # Cardiology (beds=10, lognormal ~4.0h; consult 0.15/0.50; consult time 0.5–1.5h)
            ["Sample General","Cardiology",10,0.15,0.50, "lognormal","","",4.0,0.35, "uniform",0.5,1.5,"",""],
        ]
    )

    # direct admits: allow hours=12 here; leave disabled (enabled=False) = no DA curve applied
    da_header = ["hospital","service_name","enabled","hours"] + [f"da_{i}" for i in range(12)]
    write_csv(
        f"{outdir}/direct_admits.csv",
        da_header,
        [
            ["Sample General","Medicine",False,12] + [0]*12,
            ["Sample General","Surgery", False,12] + [0]*12,
            ["Sample General","ICU",     False,12] + [0]*12,
            ["Sample General","Cardiology",False,12] + [0]*12,
        ]
    )

    # areas (A: 12 beds, ratio=2, lab_support=True)
    write_csv(
        f"{outdir}/areas.csv",
        ["hospital","area_name","beds","nurse_model","nurse_ratio","lab_support"],
        [["Sample General","A",12,"ratio",2,True]]
    )

    # doctors (12 buckets of hourly caps)
    doc_header = ["hospital","name","area","start_minute","shift_minutes","max_active_panel"] + \
                 [f"hcap_{i}" for i in range(1,13)] + \
                 ["assess_type","assess_low","assess_high","reassess_low","reassess_high"]
    write_csv(
        f"{outdir}/doctors.csv",
        doc_header,
        [
            ["Sample General","DrA1","A",0,720,10, 3,3,3,3,2,2,2,2,2,2,2,2,"uniform",12,35,8,20],
            ["Sample General","DrB1","A",720,720,10,3,3,3,3,2,2,2,2,2,2,2,2,"uniform",12,35,8,20],
            ["Sample General","DrFT1","FAST",0,720,22, 8,8,7,7,6,6,6,5,5,5,4,4,"uniform",5,12,3,8],
            ["Sample General","DrFT2","FAST",720,720,22,8,8,7,7,6,6,6,5,5,5,4,4,"uniform",5,12,3,8],
        ]
    )

    # arrivals (24h) — LWBS 200–500 per runner
    arr_header = ["hospital","hours"] + [f"walkin_{i}" for i in range(24)] + ["lwbs_low","lwbs_high","fasttrack_p","admit_p"]
    write_csv(
        f"{outdir}/arrivals.csv",
        arr_header,
        [[
            "Sample General",24,
            5,5,6,7,8,10,12,14,16,18,18,17,16,15,14,12,11,10,9,8,7,6,5,5,
            200,500,0.55,0.25
        ]]
    )

    # EMS (24h) — crew/offload uniform, p_critical=0.3, p_direct_to_bed=0.5
    ems_header = ["hospital","enabled","internal_generation","hours"] + \
                 [f"hourly_{i}" for i in range(24)] + \
                 ["ctas1","ctas2","ctas3","ctas4","ctas5","p_critical","p_direct_to_bed","download_capacity",
                  "offload_low","offload_high"] + \
                 [f"nurses_{i}" for i in range(24)] + \
                 ["crew_low","crew_high","lwbs_low","lwbs_high","fasttrack_p","admit_p"]
    write_csv(
        f"{outdir}/ems.csv",
        ems_header,
        [[
            "Sample General",True,True,24,
            0.5,0.5,1,1,2,3,4,5,6,7,7,7,7,6,6,5,4,3,2,2,1,1,0.5,0.5,
            0.04,0.15,0.48,0.28,0.05, 0.30,0.50,10,
            5,10,
            1,1,1,1,1,1,2,2,3,3,3,3,3,3,3,3,3,3,2,2,1,1,1,1,
            40,50, 45,180, 0.10,0.60
        ]]
    )

    # orders (add p_one_touch, p_three_touch)
    write_csv(
        f"{outdir}/orders.csv",
        ["hospital","proc_prob","lab_prob","di_prob",
         "proc_work_low","proc_work_high","proc_time_low","proc_time_high",
         "lab_work_low","lab_work_high","lab_time_low","lab_time_high",
         "di_work_low","di_work_high",
         "xray_low","xray_high","ct_low","ct_high","us_low","us_high",
         "p_one_touch","p_three_touch"],
        [[
            "Sample General",
            0.25,0.50,0.35,
            2,6, 10,40,
            2,5, 45,120,
            1,4,
            30,90, 60,150, 45,120,
            0.25, 0.10
        ]]
    )

    # disposition
    write_csv(
        f"{outdir}/disposition.csv",
        ["hospital","stabil_low","stabil_high","post_low","post_high"],
        [["Sample General",20,90,45,240]]
    )

    # capabilities (CT=False so CT goes external)
    write_csv(
        f"{outdir}/capabilities.csv",
        ["hospital","has_xray","has_ct","has_us","transfer_only_admit","external_di_roundtrip",
         "ext_di_low","ext_di_high","admit_transfer_low","admit_transfer_high"],
        [["Sample General",True,False,True,False,True, 90,180, 90,180]]
    )

    # fasttrack
    write_csv(
        f"{outdir}/fasttrack.csv",
        ["hospital","enabled","name","assessment_spaces","route_probability"],
        [["Sample General",True,"FAST",18,0.50]]
    )

    print(f"✳️ Wrote CSV templates under: {outdir}/ (seeded to your runner)")

# ---------- import from CSVs ----------
def import_from_csv(csv_dir: str = CSV_DIR):
    def maybe(name):
        path = os.path.join(csv_dir, name)
        return load_csv(path) if os.path.exists(path) else []

    hospitals_rows       = maybe("hospitals.csv")
    services_rows        = maybe("services.csv")
    direct_admits_rows   = maybe("direct_admits.csv")    # supports hours=12 or 24
    areas_rows           = maybe("areas.csv")
    doctors_rows         = maybe("doctors.csv")
    arrivals_rows        = maybe("arrivals.csv")
    ems_rows             = maybe("ems.csv")
    orders_rows          = maybe("orders.csv")
    disposition_rows     = maybe("disposition.csv")
    capabilities_rows    = maybe("capabilities.csv")
    fasttrack_rows       = maybe("fasttrack.csv")

    hospitals = { r["hospital"].strip(): (r.get("city","").strip() or None) for r in hospitals_rows }

    # Default skeleton
    per_h: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "inpatient_cfg": {
            "units": {},      # consult_* embedded here
            "service_to_unit_rule":"always_medicine",  # matches your lambda placeholder
            "direct_admits_enabled": False,
            "direct_admit_hours": 0,
            "direct_admit_hourly_lambda": {},
            "schema_version":1
        },
        "areas": {},
        "doctors": [],
        "arrivals": {"hours": 0, "walkin_hourly_lambda": [],
                     "lwbs_threshold_dist": {}, "fasttrack_route_probability": 0.0,
                     "admit_prob": 0.0, "schema_version":1},
        "ems": {"enabled": False, "internal_generation": False, "hours": 0,
                "hourly_lambda": [], "ctas_mix": {1:0,2:0,3:0,4:0,5:0},
                "p_critical": 0.0, "p_direct_to_bed": 0.0, "download_capacity": 0,
                "offload_service_time_dist": {}, "offload_nurses_per_hour": [],
                "crew_hospital_time_dist": {}, "lwbs_threshold_dist": {},
                "fasttrack_route_probability": 0.0, "admit_prob": 0.0, "schema_version":1},
        "triage_weights": {"schema_version":1},
        "orders": {"schema_version":1},
        "consults": {"services": {}, "schema_version":1},   # mirror for legacy
        "disposition": {"schema_version":1},
        "capabilities": {"schema_version":1},
        "fasttrack": {"schema_version":1},
    })

    # Services → build units with embedded consult fields
    for r in services_rows:
        h   = r["hospital"].strip()
        svc = r["service_name"].strip()
        eip_mean_h = Float(r.get("eip_mean_hours", "") or 0.0)
        eip_mean_min = int(eip_mean_h * 60) if eip_mean_h else 0

        beds       = Int(r["bed_base"]) or 0
        p_consult  = Float(r["p_consult"]) or 0.0
        p_admit    = Float(r["p_admit"]) or 0.0

        # LOS (HOURS) -> minutes
        los_type = (r["los_time_type"] or "").strip().lower() or "uniform"
        los_spec: Dict[str, Any] = {"type": los_type}
        if los_type == "uniform":
            low_h, high_h = Float(r["los_hours_low"]), Float(r["los_hours_high"])
            los_spec.update(low = int(low_h*60), high = int(high_h*60))
        elif los_type == "lognormal":
            los_spec.update(mean=Float(r["los_hours_mean"]), sigma=Float(r["los_hours_sigma"]), scale=60)
        elif los_type == "normal":
            los_spec.update(mu=int(Float(r["los_hours_mean"])*60), sd=int(Float(r["los_hours_sigma"])*60))
        elif los_type == "constant":
            los_spec.update(value=int(Float(r["los_hours_low"])*60))
        else:
            raise ValueError(f"Unknown los_time_type {los_type} for {svc}")

        # Consult time (HOURS) -> minutes
        ctype = (r["consult_time_type"] or "").strip().lower() or "uniform"
        c_spec: Dict[str, Any] = {"type": ctype}
        if ctype == "uniform":
            c_spec.update(low=int(Float(r["consult_hours_low"])*60), high=int(Float(r["consult_hours_high"])*60))
        elif ctype == "lognormal":
            c_spec.update(mean=Float(r["consult_hours_mean"]), sigma=Float(r["consult_hours_sigma"]), scale=60)
        elif ctype == "normal":
            c_spec.update(mu=int(Float(r["consult_hours_mean"])*60), sd=int(Float(r["consult_hours_sigma"])*60))
        elif ctype == "constant":
            c_spec.update(value=int(Float(r["consult_hours_low"])*60))
        else:
            raise ValueError(f"Unknown consult_time_type {ctype} for {svc}")

        # Unit entry (with consult fields embedded)
        per_h[h]["inpatient_cfg"]["units"][svc] = {
            "name": svc,
            "beds": beds,
            "los_dist": los_spec,
            "consult_p": p_consult,
            "consult_admit_p": p_admit,
            "consult_time_dist": c_spec,
            "eip_mean_minutes": eip_mean_min
        }

        # Mirror for legacy
        per_h[h]["consults"]["services"][svc] = {
            "p_consult": p_consult,
            "p_admit": p_admit,
            "consult_time_dist": c_spec
        }

    # Direct admits (supports hours=12 OR 24)
    for r in direct_admits_rows:
        h = r["hospital"].strip()
        svc = r["service_name"].strip()
        enabled = Bool(r["enabled"])
        hours = Int(r["hours"]) or 24
        count = 12 if hours == 12 else 24
        da = takeN("da_", r, count)
        if enabled:
            per_h[h]["inpatient_cfg"]["direct_admits_enabled"] = True
        per_h[h]["inpatient_cfg"]["direct_admit_hours"] = hours
        per_h[h]["inpatient_cfg"]["direct_admit_hourly_lambda"][svc] = da

    # Areas
    for r in areas_rows:
        h = r["hospital"].strip()
        name = r["area_name"].strip()
        per_h[h]["areas"][name] = {
            "name": name,
            "beds": Int(r["beds"]),
            "nurse_model": {
                "model": r["nurse_model"].strip(),
                "ratio": Float(r["nurse_ratio"]),
                "lab_support": Bool(r["lab_support"])
            }
        }

    # Doctors
    for r in doctors_rows:
        h = r["hospital"].strip()
        per_h[h]["doctors"].append({
            "name": r["name"].strip(),
            "area": r["area"].strip(),
            "start_minute": Int(r["start_minute"]),
            "shift_minutes": Int(r["shift_minutes"]),
            "hourly_max_signups": take_seq_1_based("hcap_", r, 12),
            "max_active_panel": Int(r["max_active_panel"]),
            "assess_time_dist": {"type": r["assess_type"], "low": Float(r["assess_low"]), "high": Float(r["assess_high"])},
            "reassess_time_dist": {"type":"uniform", "low": Float(r["reassess_low"]), "high": Float(r["reassess_high"])},
        })

    # Arrivals (24h)
    for r in arrivals_rows:
        h = r["hospital"].strip()
        per_h[h]["arrivals"].update({
            "hours": Int(r["hours"]),
            "walkin_hourly_lambda": takeN("walkin_", r, 24),
            "lwbs_threshold_dist": {"type":"uniform","low": Int(r["lwbs_low"]), "high": Int(r["lwbs_high"])},
            "fasttrack_route_probability": Float(r["fasttrack_p"]),
            "admit_prob": Float(r["admit_p"]),
        })

    # EMS (24h + nurses 24) — crew uniform
    for r in ems_rows:
        h = r["hospital"].strip()
        per_h[h]["ems"].update({
            "enabled": Bool(r["enabled"]),
            "internal_generation": Bool(r["internal_generation"]),
            "hours": Int(r["hours"]),
            "hourly_lambda": takeN("hourly_", r, 24),
            "ctas_mix": {1:Float(r["ctas1"]),2:Float(r["ctas2"]),3:Float(r["ctas3"]),4:Float(r["ctas4"]),5:Float(r["ctas5"])},
            "p_critical": Float(r["p_critical"]),
            "p_direct_to_bed": Float(r["p_direct_to_bed"]),
            "download_capacity": Int(r["download_capacity"]),
            "offload_service_time_dist": {"type":"uniform","low": Float(r["offload_low"]), "high": Float(r["offload_high"])},
            "offload_nurses_per_hour": takeN("nurses_", r, 24),
            "crew_hospital_time_dist": {"type":"uniform","low": Float(r["crew_low"]), "high": Float(r["crew_high"])},
            "lwbs_threshold_dist": {"type":"uniform","low": Int(r["lwbs_low"]), "high": Int(r["lwbs_high"])},
            "fasttrack_route_probability": Float(r["fasttrack_p"]),
            "admit_prob": Float(r["admit_p"]),
        })

    # Orders (includes p_one_touch / p_three_touch)
    for r in orders_rows:
        h = r["hospital"].strip()
        per_h[h]["orders"].update({
            "proc_prob": Float(r["proc_prob"]),
            "lab_prob": Float(r["lab_prob"]),
            "di_prob": Float(r["di_prob"]),
            "proc_work_dist": {"type":"int_range","low": Int(r["proc_work_low"]), "high": Int(r["proc_work_high"])},
            "proc_time_dist": {"type":"uniform","low": Int(r["proc_time_low"]), "high": Int(r["proc_time_high"])},
            "lab_work_dist": {"type":"int_range","low": Int(r["lab_work_low"]), "high": Int(r["lab_work_high"])},
            "lab_time_dist": {"type":"uniform","low": Int(r["lab_time_low"]), "high": Int(r["lab_time_high"])},
            "di_work_dist": {"type":"int_range","low": Int(r["di_work_low"]), "high": Int(r["di_work_high"])},
            "di_time_map": {
                "Xray": {"type":"uniform","low": Int(r["xray_low"]),"high": Int(r["xray_high"])},
                "CT":   {"type":"uniform","low": Int(r["ct_low"]),"high": Int(r["ct_high"])},
                "US":   {"type":"uniform","low": Int(r["us_low"]),"high": Int(r["us_high"])},
            },
            "p_one_touch": Float(r.get("p_one_touch", 0.0) or 0.0),
            "p_three_touch": Float(r.get("p_three_touch", 0.0) or 0.0),
        })

    # Disposition
    for r in disposition_rows:
        h = r["hospital"].strip()
        per_h[h]["disposition"].update({
            "stabilization_dist": {"type":"uniform","low": Int(r["stabil_low"]), "high": Int(r["stabil_high"])},
            "post_discharge_buffer_dist": {"type":"uniform","low": Int(r["post_low"]), "high": Int(r["post_high"])},
        })

    # Capabilities
    for r in capabilities_rows:
        h = r["hospital"].strip()
        per_h[h]["capabilities"].update({
            "has_Xray": Bool(r["has_xray"]),
            "has_CT": Bool(r["has_ct"]),
            "has_US": Bool(r["has_us"]),
            "transfer_only_admit": Bool(r["transfer_only_admit"]),
            "external_di_roundtrip": Bool(r["external_di_roundtrip"]),
            "external_di_total_time_dist": {"type":"uniform","low": Int(r["ext_di_low"]), "high": Int(r["ext_di_high"])},
            "admit_transfer_total_time_dist": {"type":"uniform","low": Int(r["admit_transfer_low"]), "high": Int(r["admit_transfer_high"])},
        })

    # FastTrack
    for r in fasttrack_rows:
        h = r["hospital"].strip()
        per_h[h]["fasttrack"].update({
            "enabled": Bool(r["enabled"]),
            "name": r["name"].strip(),
            "assessment_spaces": Int(r["assessment_spaces"]),
            "route_probability": Float(r["route_probability"]),
        })

    # ---------- upsert ----------
    with Session(engine) as s:
        for hosp, cfg in per_h.items():
            city = hospitals.get(hosp)
            row = s.query(DefaultHosp).filter_by(name=hosp).first()
            if row:
                row.city = city
                row.inpatient_cfg = cfg["inpatient_cfg"]
                row.areas         = cfg["areas"]
                row.doctors       = cfg["doctors"]
                row.arrivals      = cfg["arrivals"]
                row.ems           = cfg["ems"]
                row.triage_weights= cfg["triage_weights"]
                row.orders        = cfg["orders"]
                row.consults      = cfg["consults"]   # mirror
                row.disposition   = cfg["disposition"]
                row.capabilities  = cfg["capabilities"]
                row.fasttrack     = cfg["fasttrack"]
                print(f"🔁 Updated: {hosp}")
            else:
                s.add(DefaultHosp(
                    name=hosp, city=city,
                    inpatient_cfg=cfg["inpatient_cfg"],
                    areas=cfg["areas"],
                    doctors=cfg["doctors"],
                    arrivals=cfg["arrivals"],
                    ems=cfg["ems"],
                    triage_weights=cfg["triage_weights"],
                    orders=cfg["orders"],
                    consults=cfg["consults"],
                    disposition=cfg["disposition"],
                    capabilities=cfg["capabilities"],
                    fasttrack=cfg["fasttrack"],
                ))
                print(f"➕ Inserted: {hosp}")
        s.commit()
    print("✅ Import complete.")

# ---------- CLI ----------
def ensure_db(reset: bool = False):
    if reset and os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"🗑️ Deleted {DB_FILE}")
    Base.metadata.create_all(engine)
    print(f"🧱 Ready: {DB_FILE}")

def main_cli():
    p = argparse.ArgumentParser(description="Hospital defaults tool (aligned to current runner)")
    p.add_argument("--write-templates", action="store_true", help="Write CSV templates (seeded to runner) under hosps_csv/")
    p.add_argument("--import", dest="do_import", action="store_true", help="Import from hosps_csv/ into db.db")
    p.add_argument("--reset-db", action="store_true", help="Delete db.db and recreate schema")
    p.add_argument("--dir", default=CSV_DIR, help="CSV directory (default hosps_csv)")
    args = p.parse_args()

    ensure_db(reset=args.reset_db)

    if args.write_templates:
        write_templates(args.dir)

    if args.do_import:
        import_from_csv(args.dir)

    if not args.write_templates and not args.do_import:
        print("Nothing to do. Try:\n"
              "  python hosps_csv_tool.py --reset-db --write-templates\n"
              "  python hosps_csv_tool.py --import")

if __name__ == "__main__":
    main_cli()
