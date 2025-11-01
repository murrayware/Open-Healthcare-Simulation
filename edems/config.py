from __future__ import annotations
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

@dataclass
class FastTrackConfig:
    enabled: bool
    name: str = "FAST"
    assessment_spaces: int = 4
    route_probability: float = 0.6  # global default; per-stream overrides available
    route_rule: Optional[Callable[[Any], bool]] = None  # optional custom rule

@dataclass
class NurseModelConfig:
    model: str                      # "ratio" or "team"
    ratio: Optional[int] = None     # beds per nurse (ratio)
    team_nurses: Optional[int] = None  # number of nurses (team)
    lab_support: bool = False

@dataclass
class AreaConfig:
    name: str
    beds: int
    nurse_model: NurseModelConfig

@dataclass
class DoctorConfig:
    name: str
    area: str
    start_minute: int
    shift_minutes: int
    hourly_max_signups: List[int]
    max_active_panel: int
    assess_time_draw: Callable[[], float]
    reassess_time_draw: Callable[[], float]

@dataclass
class TriageWeights:
    w_age: float = 0.2
    w_temp: float = 0.2
    w_o2: float = -0.3
    w_bp: float = -0.1
    w_gcs: float = -0.3
    w_complaint: float = 0.2
    w_flags: float = 0.4
    ctas_bonus: Dict[int, float] = field(default_factory=lambda: {1:1.2,2:0.8,3:0.4,4:0.0,5:-0.2})

@dataclass
class ArrivalsConfig:
    hours: int
    walkin_hourly_lambda: List[float]  # can be any length; will cycle
    lwbs_threshold_draw: Callable[[], float]
    # New: stream-specific knobs (optional)
    fasttrack_route_probability: Optional[float] = None  # overrides FastTrackConfig for walk-ins
    admit_prob: Optional[float] = None  # placeholder (unused for now)

@dataclass
class EMSConfig:
    enabled: bool = True
    internal_generation: bool = True
    hours: int = 12
    hourly_lambda: List[float] = field(default_factory=lambda: [3]*12)  # can be any length; will cycle
    ctas_mix: Dict[int, float] = field(default_factory=lambda: {1:0.03,2:0.12,3:0.45,4:0.35,5:0.05})
    p_critical: float = 0.01
    p_direct_to_bed: float = 0.30
    download_capacity: int = 12
    offload_service_time_draw: Callable[[], float] = lambda: 12.0
    offload_nurses_per_hour: List[int] = field(default_factory=lambda: [1,1,2,2,3,3,3,3,2,2,1,1])
    crew_hospital_time_draw: Callable[[], float] = lambda: 25.0
    # New: EMS-specific knobs (optional)
    lwbs_threshold_draw: Optional[Callable[[], float]] = None
    fasttrack_route_probability: Optional[float] = None
    admit_prob: Optional[float] = None  # placeholder (unused for now)

@dataclass
class OrdersConfig:
    proc_prob: float
    lab_prob: float
    di_prob: float
    proc_work_draw: Callable[[], int]
    proc_time_draw: Callable[[], float]
    lab_work_draw: Callable[[], int]
    lab_time_draw: Callable[[], float]
    di_work_draw: Callable[[], int]
    di_time_draw_map: Dict[str, Callable[[], float]]
    p_one_touch:float
    p_three_touch:float

@dataclass
class DispositionConfig:
    stabilization_draw: Callable[[], float]
    post_discharge_buffer_draw: Callable[[], float]

@dataclass
class CapabilitiesConfig:
    has_Xray: bool
    has_CT: bool
    has_US: bool
    transfer_only_admit: bool
    external_di_roundtrip: bool
    external_di_total_time_draw: Callable[[], float]
    admit_transfer_total_time_draw: Callable[[], float]

# ---------- Inpatient ----------

@dataclass
class InpatientUnitSpec:
    name: str
    beds: int
    los_draw: Callable[[], float]  # minutes
    # Embedded consult knobs (service-level)
    consult_p: float = 0.0
    consult_admit_p: float = 0.0
    consult_time_draw: Optional[Callable[[], float]] = None

@dataclass
class InpatientConfig:
    units: Dict[str, InpatientUnitSpec]
    service_to_unit: Callable[[int], str] = lambda svc: "Medicine"
    direct_admits_enabled: bool = True
    direct_admit_hours: int = 12
    direct_admit_hourly_lambda: Dict[str, List[float]] = field(default_factory=dict)

# ---------- Top-level SimConfig ----------

@dataclass
class SimConfig:
    areas: Dict[str, "AreaConfig"]
    doctors: List["DoctorConfig"]
    arrivals: "ArrivalsConfig"
    ems: "EMSConfig"
    triage_weights: "TriageWeights"
    orders: "OrdersConfig"
    consults: Optional["ConsultConfig"]  # now optional; set to None when using embedded consults
    disposition: "DispositionConfig"
    capabilities: "CapabilitiesConfig"
    inpatient: "InpatientConfig"
    fasttrack: Optional[FastTrackConfig] = None
