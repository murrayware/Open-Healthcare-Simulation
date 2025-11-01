import os, random, numpy as np, pandas as pd, simpy
from edems.utils import u
from edems.eventlog import EventLog
from edems.hospital import Hospital
from edems.config import (
    SimConfig, AreaConfig, NurseModelConfig, DoctorConfig,
    ArrivalsConfig, EMSConfig, TriageWeights, OrdersConfig,
     DispositionConfig, CapabilitiesConfig,
    InpatientUnitSpec, InpatientConfig, FastTrackConfig
)
from edems.analytics import summarize_patients

random.seed(7); np.random.seed(7)

# ---- Inpatient units ----
units = {
    "Medicine": InpatientUnitSpec(
        name="Medicine",
        beds=32,  # modest community/urban unit
        # ~3–5 day LOS (lognormal with ln-mean ~4.4 → ~81h; *60 → minutes)
        los_draw=lambda: np.random.lognormal(mean=4.4, sigma=0.35) * 60,
        consult_p=0.6,          # ~30% of ED ACUTE 2/3-touch get Medicine consult
        consult_admit_p=0.95,    # ~80% of those consults admit to Medicine
        consult_time_draw=lambda: u(30, 90),  # 0.5–1.5h for consult attendance
    ),
    "Surgery": InpatientUnitSpec(
        name="Surgery",
        beds=12,
        # ~2–3.5 day LOS
        los_draw=lambda: np.random.lognormal(mean=4.1, sigma=0.40) * 60,
        consult_p=0.18,         # fewer surgical consults from ED overall
        consult_admit_p=0.7,   # higher admit if they truly need Surgery
        consult_time_draw=lambda: u(30, 75),
    ),
    "ICU": InpatientUnitSpec(
        name="ICU",
        beds=8,
        # ~1–5 days (24–120h)
        los_draw=lambda: u(24*60, 120*60),
        consult_p=0.08,         # ICU consults are uncommon
        consult_admit_p=0.90,   # high admit conditional on consult
        consult_time_draw=lambda: u(45, 120),
    ),
    "Cardiology": InpatientUnitSpec(
        name="Cardiology",
        beds=10,
        # ~1.5–3.5 days
        los_draw=lambda: np.random.lognormal(mean=4.0, sigma=0.35) * 60,
        consult_p=0.15,
        consult_admit_p=0.50,
        consult_time_draw=lambda: u(30, 90),
    ),
}

inpatient_cfg = InpatientConfig(
    units=units,
    service_to_unit=lambda svc: "Medicine",  # keep simple routing for now
    direct_admits_enabled=True,
    direct_admit_hours=12,        # daytime bias for directs
    direct_admit_hourly_lambda={},# leave empty = off for now
)

# ---- ED / EMS config ----
areas = {
    # ratio=2 → 1 nurse per 2 beds; lab_support=True keeps prior behavior
    "A": AreaConfig(name="A", beds=12, nurse_model=NurseModelConfig(model="ratio", ratio=2, lab_support=True)),
}

doctors = [
    # Acute day
    DoctorConfig(
        name="DrA1", area="A", start_minute=0, shift_minutes=12*60,
        hourly_max_signups=[3,3,3,3,2,2,2,2,2,2,2,2],
        max_active_panel=10,
        assess_time_draw=lambda: u(12, 35),
        reassess_time_draw=lambda: u(8, 20)
    ),
    # Acute evening
    DoctorConfig(
        name="DrB1", area="A", start_minute=720, shift_minutes=12*60,
        hourly_max_signups=[3,3,3,3,2,2,2,2,2,2,2,2],
        max_active_panel=10,
        assess_time_draw=lambda: u(12, 35),
        reassess_time_draw=lambda: u(8, 20)
    ),
    # Fast track day
    DoctorConfig(
        name="DrFT1", area="FAST", start_minute=0, shift_minutes=12*60,
        hourly_max_signups=[8,8,7,7,6,6,6,5,5,5,4,4],
        max_active_panel=22,
        assess_time_draw=lambda: u(5, 12),
        reassess_time_draw=lambda: u(3, 8)
    ),
    # Fast track evening
    DoctorConfig(
        name="DrFT2", area="FAST", start_minute=720, shift_minutes=12*60,
        hourly_max_signups=[8,8,7,7,6,6,6,5,5,5,4,4],
        max_active_panel=22,
        assess_time_draw=lambda: u(5, 12),
        reassess_time_draw=lambda: u(3, 8)
    )
]

arrivals = ArrivalsConfig(
    hours=24,
    # Typical diurnal curve; peak late afternoon/early evening
    walkin_hourly_lambda=[5,5,6,7,8,10,12,14,16,18,18,17,16,15,14,12,11,10,9,8,7,6,5,5],
    # Patient tolerance before LWBS (walk-ins): ~1–4h
    lwbs_threshold_draw=lambda: u(200, 500),
    fasttrack_route_probability=0.55,
    admit_prob=0.25,  # baseline admit rate for walk-ins (overall)
)

ems = EMSConfig(
    enabled=True,
    internal_generation=True,
    hours=24,
    # EMS curve peaks mid-day → early evening
    hourly_lambda=[0.5,0.5,1,1,2,3,4,5,6,7,7,7,7,6,6,5,4,3,2,2,1,1,0.5,0.5],
    ctas_mix={1:0.04, 2:0.15, 3:0.48, 4:0.28, 5:0.05},
    p_critical=0.12,
    p_direct_to_bed=0.35,
    download_capacity=6,
    offload_service_time_draw=lambda: u(5, 10),
    offload_nurses_per_hour=[1,1,1,1,1,1,2,2,3,3,3,3,3,3,3,3,3,3,2,2,1,1,1,1],
    crew_hospital_time_draw=lambda: u(40, 50),  # EMS clear ~45 ±
    lwbs_threshold_draw=lambda: u(45, 180),     # EMS patients don't LWBS until offload
    fasttrack_route_probability=0.10,           # EMS rarely FT
    admit_prob=0.60,                            # conditional admit rate for EMS arrivals
)

triage_weights = TriageWeights()

orders = OrdersConfig(
    # Order rates
    proc_prob=0.25,           # procedures less frequent than labs/DI overall
    lab_prob=0.50,            # about half get labs
    di_prob=0.35,             # ~1/3 get DI

    # Timing/work (keep simple)
    proc_work_draw=lambda: np.random.randint(2, 6),
    proc_time_draw=lambda: u(10, 40),

    lab_work_draw=lambda: np.random.randint(2, 5),
    lab_time_draw=lambda: u(45, 120),  # median ~1.5h

    di_work_draw=lambda: np.random.randint(1, 4),
    # modality turnaround (internal)
    di_time_draw_map={
        "Xray": lambda: u(30, 90),
        "CT":   lambda: u(60, 150),
        "US":   lambda: u(45, 120),
    },

    # Touch model: majority 2-touch; small tails for 1/3
    p_one_touch=0.25,
    p_three_touch=0.10,
)

consults = None  # you’re using per-unit consult params above

disposition = DispositionConfig(
    stabilization_draw=lambda: u(20, 90),
    post_discharge_buffer_draw=lambda: u(45, 240),
)

capabilities = CapabilitiesConfig(
    has_Xray=True, has_CT=False, has_US=True,   # forces CT to external path
    transfer_only_admit=False,
    external_di_roundtrip=True,
    external_di_total_time_draw=lambda: u(90, 180),  # door-to-door if modality not on site
    admit_transfer_total_time_draw=lambda: u(90, 180),
)

fasttrack = FastTrackConfig(
    enabled=True,
    name="FAST",
    assessment_spaces=18,         # 18 chairs/slots feels about right w/ 2 FT MDs
    route_probability=0.50,
)


sim_cfg = SimConfig(
    areas=areas,
    doctors=doctors,
    arrivals=arrivals,
    ems=ems,
    triage_weights=triage_weights,
    orders=orders,
    consults=consults,
    disposition=disposition,
    capabilities=capabilities,
    inpatient=inpatient_cfg,
    fasttrack=fasttrack,
)

# ---- Run one hospital (multi-day OK; 24h profiles repeat) ----
env = simpy.Environment()
elog = EventLog()
hospital = Hospital(env, sim_cfg, elog)

END_MINUTES = 30*24*60
env.run(until=END_MINUTES)

patients_df, events_df = hospital.results()

print("Patients (head):")
print(patients_df.head())
print("Events (head):")
print(events_df.head() if hasattr(events_df, "head") else events_df[:5])

os.makedirs("outputs", exist_ok=True)
patients_df.to_csv("outputs/patients.csv", index=False)
if hasattr(events_df, "to_csv"):
    events_df.to_csv("outputs/events.csv", index=False)

try:
    from edems.analytics import summarize_patients
    detailed, summary = summarize_patients(patients_df, events_df)
    print("KPI Summary (first 6 rows):")
    print(summary.head(6))
    detailed.to_csv("outputs/patient_metrics.csv", index=False)
    summary.to_csv("outputs/summary_hourly.csv", index=False)
except Exception as e:
    print("Analytics summary skipped:", e)




# === Debug outputs: numeric means + per-doctor traces ===
import numpy as np

os.makedirs("outputs/debug", exist_ok=True)

# ------- 1) Numeric means for patients_df and events_df -------
def numeric_means(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()
    num_cols = [c for c, dt in df.dtypes.items() if np.issubdtype(dt, np.number)]
    if not num_cols:
        return pd.DataFrame()
    out = df[num_cols].mean(numeric_only=True).to_frame("mean").reset_index().rename(columns={"index": "column"})
    out["count_nonnull"] = df[num_cols].count().values
    return out

patients_means = numeric_means(patients_df)
patients_means.to_csv("outputs/debug/patients_numeric_means.csv", index=False)

events_means = numeric_means(events_df if hasattr(events_df, "dtypes") else pd.DataFrame())
events_means.to_csv("outputs/debug/events_numeric_means.csv", index=False)

print("\nSaved numeric means to:")
print("  outputs/debug/patients_numeric_means.csv")
print("  outputs/debug/events_numeric_means.csv")

# ------- 2) Per-doctor traces: 3 patients per doctor -------
# Try to be defensive about column names
if hasattr(events_df, "columns"):
    df_e = events_df.copy()
    # Identify time-like column
    time_col = None
    for cand in ["time", "t", "minute", "timestamp"]:
        if cand in df_e.columns:
            time_col = cand
            break
    if time_col is None:
        # If your EventLog uses a different name, add it here
        raise KeyError("Could not find time column in events_df (looked for 'time','t','minute','timestamp').")

    # Identify event name column (keep everything, but use it for human reading)
    event_col = "event" if "event" in df_e.columns else ("name" if "name" in df_e.columns else None)

    # Doctor + pid columns (doctor may be missing for some rows; that's okay)
    pid_col = "pid" if "pid" in df_e.columns else None
    doc_col = "doctor" if "doctor" in df_e.columns else None

    if pid_col is None:
        raise KeyError("events_df is missing 'pid' column.")

    # If no explicit 'doctor' column exists, we can still pick random PIDs globally
    doctors = sorted(df_e[doc_col].dropna().unique().tolist()) if doc_col in df_e else []

    traces_list = []

    if doctors:
        # For each doctor, pick up to 3 patients by the earliest assess_start with that doc
        if event_col is not None:
            assess_mask = (df_e[event_col] == "assess_start")
        else:
            # Fallback: use the doc's earliest event per PID as proxy
            assess_mask = df_e[doc_col].notna()

        for doc in doctors:
            df_doc = df_e[df_e[doc_col] == doc]
            # earliest time per pid for this doc (prefer assess_start)
            df_doc_assess = df_doc[assess_mask]
            if df_doc_assess.empty:
                # fallback to any events from this doc
                df_doc_assess = df_doc

            if df_doc_assess.empty:
                continue

            pid_order = (df_doc_assess[[pid_col, time_col]]
                        .sort_values(time_col)
                        .drop_duplicates(pid_col))[pid_col].tolist()

            chosen_pids = pid_order[:3] if len(pid_order) >= 3 else pid_order

            if not chosen_pids:
                continue

            # Pull full event sequence for those PIDs (not just rows labeled with this doctor)
            df_trace = (df_e[df_e[pid_col].isin(chosen_pids)]
                        .copy()
                        .sort_values([pid_col, time_col]))
            df_trace.insert(0, "doctor_focus", doc)  # make it easy to filter later
            traces_list.append(df_trace)
    else:
        # No doctor column; just pick 3 random PIDs overall for a single generic trace
        # (keeps you unblocked if certain event logs don't tag doctor)
        rng = np.random.default_rng(7)
        all_pids = df_e[pid_col].dropna().unique().tolist()
        chosen_pids = rng.choice(all_pids, size=min(3, len(all_pids)), replace=False).tolist()
        df_trace = df_e[df_e[pid_col].isin(chosen_pids)].copy().sort_values([pid_col, time_col])
        df_trace.insert(0, "doctor_focus", "UNKNOWN")
        traces_list = [df_trace]

    if traces_list:
        traces = pd.concat(traces_list, ignore_index=True)
        traces.to_csv("outputs/debug/doctor_patient_traces.csv", index=False)
        print("Saved per-doctor traces to: outputs/debug/doctor_patient_traces.csv")
        if doctors:
            # quick console index of which PIDs were chosen per doctor
            print("\nSampled PIDs per doctor:")
            for doc in (doctors):
                pids = (traces.loc[traces["doctor_focus"] == doc, pid_col]
                              .drop_duplicates().tolist())
                print(f"  {doc}: {pids[:3]}")
    else:
        print("No traces generated (no doctor-tagged events or no events found).")
