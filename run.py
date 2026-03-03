import os, random, numpy as np, pandas as pd, simpy
from edems.utils import u
from edems.eventlog import EventLog
from edems.hospital import Hospital
from edems.config import (
    SimConfig, AreaConfig, NurseModelConfig, DoctorConfig,
    ArrivalsConfig, EMSConfig, TriageWeights, OrdersConfig,
    DispositionConfig, CapabilitiesConfig,
    InpatientUnitSpec, InpatientConfig, FastTrackConfig   # <-- FT
)
from edems.analytics import summarize_patients

random.seed(7); np.random.seed(7)

# ---- Inpatient units ----
units = {
    "Medicine": InpatientUnitSpec(name="Medicine", beds=20, los_draw=lambda: np.random.lognormal(mean=4.5, sigma=0.35)*60),
    "Surgery":  InpatientUnitSpec(name="Surgery",  beds=12, los_draw=lambda: np.random.lognormal(mean=4.2, sigma=0.40)*60),
    "ICU":      InpatientUnitSpec(name="ICU",      beds=6,  los_draw=lambda: u(12*60, 72*60)),
}

def service_to_unit(service_id: int) -> str:
    mod = service_id % 10
    if mod in (1,2,3,4,5): return "Medicine"
    if mod in (6,7,8):     return "Surgery"
    return "ICU"

inpatient_cfg = InpatientConfig(
    units=units,
    service_to_unit=service_to_unit,
    direct_admits_enabled=True,
    direct_admit_hours=12,
    direct_admit_hourly_lambda={
        "Medicine": [2,2,3,3,4,4,4,4,3,3,2,2],
        "Surgery":  [1,1,1,2,2,2,2,2,2,1,1,1],
        "ICU":      [0.2]*12,
    },
)

# ---- ED / EMS config ----
areas = {
    "A": AreaConfig(name="A", beds=10, nurse_model=NurseModelConfig(model="ratio", ratio=2, lab_support=True)),
}

doctors = [
    # A side
    DoctorConfig(
        name="DrA1", area="A", start_minute=0, shift_minutes=12*60,
        hourly_max_signups=[3,3,2,2,2,2,2,2,2,2,2,2],  # 12 entries
        max_active_panel=10,
        assess_time_draw=lambda: u(15, 60),
        reassess_time_draw=lambda: u(10, 30)
    ),
    # B side
    DoctorConfig(
        name="DrB1", area="A", start_minute=720, shift_minutes=12*60,
        hourly_max_signups=[4,3,3,3,2,2,2,2,2,2,2,2],
        max_active_panel=12,
        assess_time_draw=lambda: u(15, 60),
        reassess_time_draw=lambda: u(10, 30)
    ),
    # Fast Track
    DoctorConfig(
        name="DrFT1", area="FAST", start_minute=0, shift_minutes=12*60,
        hourly_max_signups=[8,8,7,7,6,6,6,5,5,5,4,4],
        max_active_panel=25,
        assess_time_draw=lambda: u(6, 15),
        reassess_time_draw=lambda: u(3, 8)
    ),
    DoctorConfig(
        name="DrFT2", area="FAST", start_minute=720, shift_minutes=12*60,
        hourly_max_signups=[8,8,7,7,6,6,6,5,5,5,4,4],
        max_active_panel=25,
        assess_time_draw=lambda: u(6, 15),
        reassess_time_draw=lambda: u(3, 8)
    )
]


arrivals = ArrivalsConfig(
    hours=12,
    walkin_hourly_lambda=[6,8,10,12,14,16,18,16,14,12,10,8],
    lwbs_threshold_draw=lambda: u(60,240),
)

ems = EMSConfig(
    enabled=True,
    internal_generation=True,
    hours=12,
    hourly_lambda=[2,3,4,5,6,7,7,6,5,4,3,2],
    ctas_mix={1:0.03,2:0.12,3:0.45,4:0.35,5:0.05},
    p_critical=0.01,
    p_direct_to_bed=0.30,
    download_capacity=12,
    offload_service_time_draw=lambda: np.random.uniform(8,18),
    offload_nurses_per_hour=[1,1,2,2,3,3,3,3,2,2,1,1],
    crew_hospital_time_draw=lambda: 25.0
)

triage_weights = TriageWeights()

orders = OrdersConfig(
    proc_prob=0.30, lab_prob=0.55, di_prob=0.35,
    proc_work_draw=lambda: np.random.randint(3,9),
    proc_time_draw=lambda: u(10,40),
    lab_work_draw=lambda: np.random.randint(2,6),
    lab_time_draw=lambda: u(30,120),
    di_work_draw=lambda: np.random.randint(2,6),
    di_time_draw_map={
        "Xray": lambda: u(20,60),
        "CT":   lambda: u(40,120),
        "US":   lambda: u(30,120),
    },
    p_one_touch=0.15,
    p_three_touch=0.25
)

consults = None  # Using embedded consult config in InpatientUnitSpec

disposition = DispositionConfig(
    stabilization_draw=lambda: u(30,120),
    post_discharge_buffer_draw=lambda: u(60,600),
)

capabilities = CapabilitiesConfig(
    has_Xray=True, has_CT=False, has_US=True,
    transfer_only_admit=False,
    external_di_roundtrip=True,
    external_di_total_time_draw=lambda: u(100,180),
    admit_transfer_total_time_draw=lambda: u(90,180),
)

# --- Fast Track config (enable + routing) ---
fasttrack = FastTrackConfig(
    enabled=True,
    name="FAST",
    assessment_spaces=20,
    route_probability=0.55,
    route_rule=lambda p: (p.ctas >= 3)
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
    fasttrack=fasttrack,   # <-- FT plugged in
)

# ---- Run one hospital ----
env = simpy.Environment()
elog = EventLog()
hospital = Hospital(env, sim_cfg, elog)

END_MINUTES = 24*60
env.run(until=END_MINUTES)

patients_df, events_df = hospital.results()

print("Patients (head):")
print(patients_df.head())
print("\nEvents (head):")
print(events_df.head())

# Save outputs
os.makedirs("outputs", exist_ok=True)
patients_df.to_csv("outputs/patients.csv", index=False)
events_df.to_csv("outputs/events.csv", index=False)

# Quick summary
detailed, summary = summarize_patients(patients_df, events_df)
print("\nKPI Summary (means):")
print(summary)
detailed.to_csv("outputs/patient_metrics.csv", index=False)


patients_df, events_df = hospital.results()
detailed, summary = summarize_patients(patients_df, events_df)
