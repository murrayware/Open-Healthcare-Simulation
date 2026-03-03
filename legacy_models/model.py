import simpy
import random
import numpy as np
import pandas as pd
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple

# =========================
# Utilities & Event logging
# =========================

def u(lo, hi):
    return random.uniform(lo, hi)

class EventLog:
    def __init__(self):
        self.rows = []
    def add(self, t, etype, **kwargs):
        row = {"t": float(t), "event": etype}
        row.update(kwargs)
        self.rows.append(row)
    def to_df(self):
        return pd.DataFrame(self.rows)

# =========================
# Config dataclasses
# =========================

@dataclass
class NurseModelConfig:
    model: str                      # "ratio" or "team"
    ratio: Optional[int] = None     # beds per nurse (ratio)
    team_nurses: Optional[int] = None
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
    assess_time_draw: Callable[[], float] = lambda: u(15, 100)
    reassess_time_draw: Callable[[], float] = lambda: u(15, 100)

@dataclass
class TriageWeights:
    w_age: float = 0.2
    w_temp: float = 0.2
    w_o2: float = -0.3
    w_bp: float = -0.1
    w_gcs: float = -0.3
    w_complaint: float = 0.2
    w_flags: float = 0.4
    ctas_bonus: Dict[int, float] = field(default_factory=lambda: {1: 1.2, 2: 0.8, 3: 0.4, 4: 0.0, 5: -0.2})

@dataclass
class ArrivalsConfig:
    hours: int
    walkin_hourly_lambda: List[float]
    lwbs_threshold_draw: Callable[[], float] = lambda: u(60, 240)

@dataclass
class EMSConfig:
    enabled: bool = True
    internal_generation: bool = True
    hours: int = 12
    hourly_lambda: List[float] = field(default_factory=lambda: [3]*12)
    ctas_mix: Dict[int, float] = field(default_factory=lambda: {1:0.03, 2:0.12, 3:0.45, 4:0.35, 5:0.05})
    p_critical: float = 0.01
    p_direct_to_bed: float = 0.3
    download_capacity: int = 12
    offload_service_time_draw: Callable[[], float] = lambda: np.random.uniform(8, 20)
    offload_nurses_per_hour: List[int] = field(default_factory=lambda: [1,1,2,2,3,3,3,3,2,2,1,1])
    crew_hospital_time_draw: Callable[[], float] = lambda: 25.0

@dataclass
class OrdersConfig:
    proc_prob: float = 0.30
    lab_prob: float = 0.55
    di_prob: float = 0.35
    proc_work_draw: Callable[[], int] = lambda: random.randint(3, 8)
    proc_time_draw: Callable[[], float] = lambda: u(10, 40)
    lab_work_draw: Callable[[], int] = lambda: random.randint(2, 6)
    lab_time_draw: Callable[[], float] = lambda: u(30, 120)
    di_work_draw: Callable[[], int] = lambda: random.randint(2, 6)
    di_time_draw_map: Dict[str, Callable[[], float]] = field(default_factory=lambda: {
        "Xray": lambda: u(20, 60),
        "CT":   lambda: u(40, 120),
        "US":   lambda: u(30, 120),
    })

@dataclass
class ConsultConfig:
    service_count: int = 40
    request_prob: float = 0.25
    admit_prob_by_service: Callable[[int], float] = lambda s: 0.5
    local_boarding_time_draw: Callable[[], float] = lambda: u(180, 300)

@dataclass
class DispositionConfig:
    stabilization_draw: Callable[[], float] = lambda: u(30, 120)
    post_discharge_buffer_draw: Callable[[], float] = lambda: u(60, 600)

@dataclass
class CapabilitiesConfig:
    has_Xray: bool = True
    has_CT: bool = True
    has_US: bool = True
    transfer_only_admit: bool = False
    external_di_roundtrip: bool = True
    external_di_total_time_draw: Callable[[], float] = lambda: u(90, 180)
    admit_transfer_total_time_draw: Callable[[], float] = lambda: u(60, 180)

@dataclass
class SimConfig:
    areas: Dict[str, AreaConfig]
    doctors: List[DoctorConfig]
    arrivals: ArrivalsConfig
    ems: EMSConfig
    triage_weights: TriageWeights
    orders: OrdersConfig
    consults: ConsultConfig
    disposition: DispositionConfig
    capabilities: CapabilitiesConfig
    # horizon knobs
    sim_minutes: Optional[int] = None
    tail_minutes: int = 240

# =========================
# Core entities
# =========================

class Patient:
    _id = 0
    def __init__(self, env, area_name, eventlog: EventLog, triage_w: TriageWeights, lwbs_draw: Callable[[], float], ctas: Optional[int] = None):
        Patient._id += 1
        self.id = Patient._id
        self.env = env
        self.area = area_name
        self.eventlog = eventlog

        # triage features
        self.age = random.randint(18, 95)
        self.temp = u(36.0, 40.5)
        self.o2 = u(80, 100)
        self.bp = u(70, 180)
        self.gcs = random.randint(3, 15)
        self.complaint = random.randint(1, 168)
        self.is_trauma = random.random() < 0.10
        self.is_mh = random.random() < 0.12
        self.ctas = ctas if ctas else 3

        self.acuity = self.compute_acuity(triage_w)
        self.lwbs_threshold = lwbs_draw()

        # state
        self.arrival_time = env.now
        self.bed_id: Optional[int] = None
        self.initial_assessed = False
        self.orders_1_done = True
        self.orders_2_done = True
        self.consult_service: Optional[int] = None
        self.admitted = False
        self.boarding_start = None
        self.disposition_time = None
        self.lwbs = False
        self.is_critical_ems = False
        self.path: Optional[str] = None  # "acute" or "fasttrack"

        eventlog.add(env.now, "arrival", pid=self.id, area=self.area, acuity=self.acuity, ctas=self.ctas)

    def compute_acuity(self, w: TriageWeights):
        flags = int(self.is_trauma) + int(self.is_mh)
        score = (
            w.w_age * (self.age/100.0) +
            w.w_temp * ((self.temp-36.0)/4.5) +
            w.w_o2 * ((100 - self.o2)/20.0) +
            w.w_bp * ((120 - self.bp)/50.0) +
            w.w_gcs * ((15 - self.gcs)/12.0) +
            w.w_complaint * (self.complaint/168.0) +
            w.w_flags * flags +
            w.ctas_bonus.get(getattr(self, "ctas", 3), 0.0)
        )
        return score

class Doctor:
    def __init__(self, cfg: DoctorConfig, eventlog: EventLog):
        self.cfg = cfg
        self.eventlog = eventlog
        self.active_panel: set[int] = set()
        self.new_signup_log: Dict[Tuple[int,int], int] = defaultdict(int)
        self.resource = None  # SimPy Resource

    def on_shift(self, t):
        day_min = int(t % (24*60))
        start = self.cfg.start_minute
        end = (self.cfg.start_minute + self.cfg.shift_minutes) % (24*60)
        if self.cfg.shift_minutes >= 24*60: return True
        if start <= end:
            return start <= day_min < end
        return not (end <= day_min < start)

    def _hour_index(self, t):
        day_min = int(t % (24*60))
        return (day_min - self.cfg.start_minute) // 60

    def can_signup_now(self, t):
        if not self.on_shift(t): return False
        h = self._hour_index(t)
        if h < 0 or h >= len(self.cfg.hourly_max_signups): return False
        day = int(t // (24*60))
        quota = self.cfg.hourly_max_signups[h]
        return self.new_signup_log[(day, h)] < quota

    def register_signup(self, t):
        day = int(t // (24*60))
        h = self._hour_index(t)
        self.new_signup_log[(day, h)] += 1

# =========================
# Acute runtime (beds + nurses + doctors + EMS)
# =========================

class AreaRuntime:
    def __init__(self, env, cfg: AreaConfig, eventlog: EventLog):
        self.env = env
        self.cfg = cfg
        self.eventlog = eventlog
        self.beds_capacity = cfg.beds
        self.beds_in_use = 0
        self.bed_semaphore = simpy.Resource(env, capacity=cfg.beds)
        self.waiting: List[Patient] = []

        if cfg.nurse_model.model == "team":
            self.orders_fifo = deque()
        else:
            self.orders_by_bed = {b: deque() for b in range(cfg.beds)}

        self.nurse_procs = []
        if cfg.nurse_model.model == "team":
            for i in range(cfg.nurse_model.team_nurses or 1):
                self.nurse_procs.append(env.process(self.team_nurse_worker(i)))
        else:
            ratio = max(1, cfg.nurse_model.ratio or 2)
            groups = [list(range(b, min(b+ratio, cfg.beds))) for b in range(0, cfg.beds, ratio)]
            for i, bed_group in enumerate(groups):
                self.nurse_procs.append(env.process(self.ratio_nurse_worker(i, bed_group)))

    def enqueue_waiting(self, p: Patient):
        self.waiting.append(p)
        self.waiting.sort(key=lambda q: (-q.acuity, q.arrival_time))
        self.eventlog.add(self.env.now, "queued_for_bed", pid=p.id, area=self.cfg.name, acuity=p.acuity)

    def get_next_for_bed(self) -> Optional[Patient]:
        if not self.waiting: return None
        return self.waiting.pop(0)

    def _handle_order(self, order: dict):
        typ = order["type"]
        if typ == "proc":
            return order["time_draw"]()
        elif typ == "lab":
            return 5.0 if self.cfg.nurse_model.lab_support else order["time_draw"]()
        elif typ == "di":
            return 10.0
        return 0.0

    def ratio_nurse_worker(self, nurse_idx: int, beds: List[int]):
        while True:
            worked = False
            for b in beds:
                fifo = self.orders_by_bed[b]
                if fifo:
                    t0, pid, order = fifo.popleft()
                    worked = True
                    self.eventlog.add(self.env.now, "order_start", pid=pid, area=self.cfg.name, bed=b, nurse=nurse_idx, order=order["type"], extra=order.get("modality"))
                    dt = self._handle_order(order)
                    yield self.env.timeout(dt)
                    self.eventlog.add(self.env.now, "order_done", pid=pid, area=self.cfg.name, bed=b, nurse=nurse_idx, order=order["type"], extra=order.get("modality"))
            if not worked:
                yield self.env.timeout(1)

    def team_nurse_worker(self, nurse_idx: int):
        while True:
            if self.orders_fifo:
                t0, pid, order, bed = self.orders_fifo.popleft()
                self.eventlog.add(self.env.now, "order_start", pid=pid, area=self.cfg.name, bed=bed, nurse=nurse_idx, order=order["type"], extra=order.get("modality"))
                dt = self._handle_order(order)
                yield self.env.timeout(dt)
                self.eventlog.add(self.env.now, "order_done", pid=pid, area=self.cfg.name, bed=bed, nurse=nurse_idx, order=order["type"], extra=order.get("modality"))
            else:
                yield self.env.timeout(1)

    def enqueue_order(self, bed_id: int, pid: int, order: dict):
        if self.cfg.nurse_model.model == "team":
            self.orders_fifo.append((self.env.now, pid, order, bed_id))
        else:
            self.orders_by_bed[bed_id].append((self.env.now, pid, order))

class AcuteCore:
    """Acute engine: uses external env & eventlog. No internal walk-in generator. EMS optional."""
    def __init__(self, env, eventlog, cfg: SimConfig):
        self.env = env
        self.eventlog = eventlog
        self.cfg = cfg

        # horizon
        if cfg.sim_minutes is not None:
            self.end_time = cfg.sim_minutes
        else:
            walk = (cfg.arrivals.hours or 0) * 60
            ems_h = ((cfg.ems.hours or 0) * 60) if cfg.ems and cfg.ems.enabled else 0
            self.end_time = max(walk, ems_h) + (cfg.tail_minutes or 0)

        # areas
        self.areas: Dict[str, AreaRuntime] = {name: AreaRuntime(env, a_cfg, eventlog) for name, a_cfg in cfg.areas.items()}

        # doctors
        self.doctors: List[Doctor] = [Doctor(d, eventlog) for d in cfg.doctors]
        for d in self.doctors:
            d.resource = simpy.Resource(env, capacity=1)

        # bed map
        self.bed_pid: Dict[str, List[Optional[int]]] = {name: [None]*a.cfg.beds for name, a in self.areas.items()}
        # patients
        self.patients: Dict[int, Patient] = {}

        # EMS
        self.ems_cfg = cfg.ems
        self.ems_fifo = deque()
        if self.ems_cfg.enabled:
            init_tokens = (self.ems_cfg.offload_nurses_per_hour or [1])[0]
            self.offload_tokens = simpy.Container(env, capacity=1000, init=init_tokens)
            self.download_area = simpy.Resource(env, capacity=self.ems_cfg.download_capacity)
            if self.ems_cfg.offload_nurses_per_hour:
                self.env.process(self._offload_scheduler(self.ems_cfg.offload_nurses_per_hour))
            self.env.process(self._ems_coordinator_loop())
            if self.ems_cfg.internal_generation:
                self.env.process(self._ems_arrivals_internal())

        # area allocators & doctor loops
        for name in self.areas:
            self.env.process(self._bed_allocator_loop(name))
        for d in self.doctors:
            self.env.process(self._doctor_loop(d))

    # ----- external API -----
    def add_acute_walkin(self, area_name: str, p: Patient):
        p.path = "acute"
        self.patients[p.id] = p
        self.areas[area_name].enqueue_waiting(p)

    def results_patients_df(self) -> pd.DataFrame:
        rows = []
        for p in self.patients.values():
            rows.append({
                "pid": p.id, "path": "acute", "area": p.area, "bed": p.bed_id,
                "arrival": p.arrival_time, "ctas": p.ctas, "lwbs": p.lwbs,
                "admitted": p.admitted, "disposition_time": p.disposition_time,
                "los_minutes": (p.disposition_time - p.arrival_time) if p.disposition_time else None,
                "initial_assessed": p.initial_assessed, "orders1_done": p.orders_1_done,
                "orders2_done": p.orders_2_done, "consult_service": p.consult_service,
                "acuity": p.acuity
            })
        return pd.DataFrame(rows)

    # ----- EMS machinery -----
    def _offload_scheduler(self, schedule: List[int]):
        idx = 0
        while True:
            target = schedule[idx % len(schedule)]
            delta = target - self.offload_tokens.level
            if delta > 0:
                yield self.offload_tokens.put(delta)
            elif delta < 0:
                yield self.offload_tokens.get(-delta)
            yield self.env.timeout(60 - (self.env.now % 60))
            idx += 1

    def _draw_ctas(self):
        items = sorted(self.ems_cfg.ctas_mix.items())
        r = random.random(); c = 0.0
        for level, prob in items:
            c += prob
            if r < c: return level
        return 3

    def _ems_arrivals_internal(self):
        hours = self.ems_cfg.hours
        hourly = self.ems_cfg.hourly_lambda
        lwbs_draw = self.cfg.arrivals.lwbs_threshold_draw
        tw = self.cfg.triage_weights
        area_names = list(self.areas.keys())
        for _ in range(hours):
            k = np.random.poisson(hourly[_ % len(hourly)])
            offsets = sorted(np.random.randint(0, 60, size=k).tolist())
            for off in offsets:
                yield self.env.timeout(max(0, off - (self.env.now % 60)))
                area = random.choice(area_names)
                p = Patient(self.env, area, self.eventlog, tw, lwbs_draw, ctas=self._draw_ctas())
                p.is_critical_ems = (random.random() < self.ems_cfg.p_critical)
                p.path = "acute"
                self.patients[p.id] = p
                self.eventlog.add(self.env.now, "ems_arrival", pid=p.id, area=area, ctas=p.ctas, critical=p.is_critical_ems)
                self.ems_fifo.append((self.env.now, p.id))
            if self.env.now % 60 != 0:
                yield self.env.timeout(60 - (self.env.now % 60))

    def _ems_coordinator_loop(self):
        while True:
            if not self.ems_fifo:
                yield self.env.timeout(1); continue
            _, pid = self.ems_fifo[0]
            p = self.patients.get(pid)
            if p is None:
                self.ems_fifo.popleft(); continue
            if self.offload_tokens.level < 1:
                yield self.env.timeout(1); continue

            self.ems_fifo.popleft()
            yield self.offload_tokens.get(1)
            offload_start = self.env.now
            crew_hold = self.ems_cfg.crew_hospital_time_draw()
            self.eventlog.add(self.env.now, "ems_offload_start", pid=pid, area=p.area)
            self.env.process(self._mark_crew_clear(pid, offload_start, crew_hold))
            svc = self.ems_cfg.offload_service_time_draw()

            path = None
            if p.is_critical_ems:
                while True:
                    if self._area_has_free_bed(p.area) and self._area_has_accepting_doctor(p.area):
                        yield self.env.timeout(svc)
                        path = "direct_bed_critical"; yield from self._place_direct_to_bed(p); break
                    yield self.env.timeout(1)
            else:
                routed = False
                if random.random() < self.ems_cfg.p_direct_to_bed:
                    if self._area_has_free_bed(p.area) and self._area_has_accepting_doctor(p.area):
                        yield self.env.timeout(svc)
                        path = "direct_bed"; yield from self._place_direct_to_bed(p); routed = True
                if not routed:
                    if self._download_slot_available():
                        with self.download_area.request() as req:
                            yield req; yield self.env.timeout(svc)
                            path = "download"; self.areas[p.area].enqueue_waiting(p)
                    else:
                        yield self.env.timeout(svc)
                        path = "waiting_room"; self.areas[p.area].enqueue_waiting(p)

            self.eventlog.add(self.env.now, "ems_offload_end", pid=pid, area=p.area, path=path)
            yield self.offload_tokens.put(1)

    def _mark_crew_clear(self, pid: int, offload_start: float, crew_hold: float):
        yield self.env.timeout(max(0.0, crew_hold))
        self.eventlog.add(offload_start + crew_hold, "ems_crew_clear", pid=pid, minutes=crew_hold)

    def _place_direct_to_bed(self, p: Patient):
        area = self.areas[p.area]
        with area.bed_semaphore.request() as req:
            yield req
            bed_list = self.bed_pid[p.area]
            bed_id = bed_list.index(None)
            bed_list[bed_id] = p.id
            area.beds_in_use += 1
            p.bed_id = bed_id
            self.eventlog.add(self.env.now, "bed_in", pid=p.id, area=p.area, bed=bed_id)
            self.env.process(self._in_bed_flow(p, p.area, bed_id))

    def _area_has_free_bed(self, area_name: str) -> bool:
        a = self.areas[area_name]
        return a.beds_in_use < a.beds_capacity

    def _area_has_accepting_doctor(self, area_name: str) -> bool:
        t = self.env.now
        for d in self.doctors:
            if d.cfg.area != area_name: continue
            if d.on_shift(t) and d.can_signup_now(t) and (len(d.active_panel) < d.cfg.max_active_panel):
                return True
        return False

    def _download_slot_available(self) -> bool:
        return len(self.download_area.users) < self.download_area.capacity

    # ----- bed allocators / doctor loops -----
    def _bed_allocator_loop(self, area_name: str):
        area = self.areas[area_name]
        while True:
            if area.waiting:
                to_remove = []
                for p in list(area.waiting):
                    if (self.env.now - p.arrival_time) > p.lwbs_threshold:
                        p.lwbs = True
                        self.eventlog.add(self.env.now, "lwbs", pid=p.id, area=area_name)
                        to_remove.append(p)
                if to_remove:
                    area.waiting = [q for q in area.waiting if q not in to_remove]
            if area.beds_in_use < area.beds_capacity and area.waiting:
                p = area.get_next_for_bed()
                if p and not p.lwbs:
                    with area.bed_semaphore.request() as req:
                        yield req
                        bed_list = self.bed_pid[area_name]
                        bed_id = bed_list.index(None)
                        bed_list[bed_id] = p.id
                        area.beds_in_use += 1
                        p.bed_id = bed_id
                        self.eventlog.add(self.env.now, "bed_in", pid=p.id, area=area_name, bed=bed_id)
                        self.env.process(self._in_bed_flow(p, area_name, bed_id))
            else:
                yield self.env.timeout(1)

    def _doctor_loop(self, doc: Doctor):
        while True:
            t = self.env.now
            if not doc.on_shift(t):
                yield self.env.timeout(1); continue
            area_name = doc.cfg.area
            cands = self._patients_needing_doc(area_name, doc)
            if not cands:
                yield self.env.timeout(1); continue
            p = cands[0]
            is_new = (p.id not in doc.active_panel)
            if is_new:
                if (len(doc.active_panel) >= doc.cfg.max_active_panel) or (not doc.can_signup_now(t)):
                    p = next((q for q in cands if q.id in doc.active_panel), None)
                    if p is None:
                        yield self.env.timeout(1); continue
                else:
                    doc.register_signup(t)
                    doc.active_panel.add(p.id)
                    self.eventlog.add(self.env.now, "doc_signup", pid=p.id, doctor=doc.cfg.name, area=area_name)

            self.eventlog.add(self.env.now, "doc_assess_start", pid=p.id, doctor=doc.cfg.name, area=area_name)
            with doc.resource.request() as req:
                yield req
                dur = doc.cfg.assess_time_draw() if not p.initial_assessed else doc.cfg.reassess_time_draw()
                yield self.env.timeout(dur)
            self.eventlog.add(self.env.now, "doc_assess_done", pid=p.id, doctor=doc.cfg.name, area=area_name, duration=dur)

            if not p.initial_assessed:
                p.initial_assessed = True
                self._place_orders(p, area_name, first_round=True)
            else:
                if not p.orders_2_done and random.random() < 0.6:
                    self._place_orders(p, area_name, first_round=False)
            yield self.env.timeout(1)

    def _patients_needing_doc(self, area_name: str, doc: Doctor) -> List[Patient]:
        out = []
        for bed_id, pid in enumerate(self.bed_pid[area_name]):
            if pid is None: continue
            p = self.patients[pid]
            if not p.initial_assessed:
                out.append(p)
            else:
                if not p.orders_1_done or not p.orders_2_done:
                    out.append(p)
        out.sort(key=lambda q: (q.initial_assessed, -q.acuity, q.arrival_time))
        return out

    def _place_orders(self, p: Patient, area_name: str, first_round: bool):
        area = self.areas[area_name]; oc = self.cfg.orders; caps = self.cfg.capabilities

        def make_order(typ: str):
            if typ == "proc":
                return {"type": "proc", "work": oc.proc_work_draw(), "time_draw": oc.proc_time_draw}
            if typ == "lab":
                return {"type": "lab", "work": oc.lab_work_draw(), "time_draw": oc.lab_time_draw}
            if typ == "di":
                modality, draw = random.choice(list(oc.di_time_draw_map.items()))
                ok = not ((modality=="CT" and not caps.has_CT) or (modality=="US" and not caps.has_US) or (modality=="Xray" and not caps.has_Xray))
                if not ok:
                    self.eventlog.add(self.env.now, "transfer_needed", pid=p.id, reason=f"DI_{modality}")
                    self.env.process(self._external_di_transfer_flow(p, modality))
                    return None
                return {"type": "di", "modality": modality, "work": oc.di_work_draw(), "time_draw": draw}
            raise ValueError("unknown order type")

        will_proc = random.random() < oc.proc_prob
        will_lab  = random.random() < oc.lab_prob
        will_di   = (random.random() < oc.di_prob) if first_round else False

        orders = []
        if will_proc: orders.append(make_order("proc"))
        if will_lab:  orders.append(make_order("lab"))
        if will_di:
            di_od = make_order("di")
            if di_od: orders.append(di_od)

        if first_round and any(o for o in orders if o): p.orders_1_done = False
        if (not first_round) and any(o for o in orders if o): p.orders_2_done = False

        for od in [o for o in orders if o]:
            self.eventlog.add(self.env.now, "order_enqueued", pid=p.id, area=area_name, bed=p.bed_id, order=od["type"], extra=od.get("modality"))
            area.enqueue_order(p.bed_id, p.id, od)

    def _external_di_transfer_flow(self, p: Patient, modality: str):
        caps = self.cfg.capabilities
        t_total = caps.external_di_total_time_draw()
        self.eventlog.add(self.env.now, "external_di_start", pid=p.id, modality=modality, minutes=t_total)
        yield self.env.timeout(t_total)
        self.eventlog.add(self.env.now, "external_di_done", pid=p.id, modality=modality)
        if not p.initial_assessed:
            p.orders_1_done = True
        else:
            p.orders_2_done = True

    def _in_bed_flow(self, p: Patient, area_name: str, bed_id: int):
        area = self.areas[area_name]
        consults = self.cfg.consults; disp = self.cfg.disposition; caps = self.cfg.capabilities

        def bed_orders_pending():
            if area.cfg.nurse_model.model == "team":
                return any(pid == p.id for _, pid, _, _ in area.orders_fifo)
            else:
                return any(pid == p.id for _, pid, _ in area.orders_by_bed[bed_id])

        while True:
            if not p.orders_1_done and not bed_orders_pending():
                p.orders_1_done = True
                self.eventlog.add(self.env.now, "orders_first_round_done", pid=p.id, area=area_name, bed=bed_id)
            if p.initial_assessed and (not p.orders_2_done) and not bed_orders_pending():
                p.orders_2_done = True
                self.eventlog.add(self.env.now, "orders_second_round_done", pid=p.id, area=area_name, bed=bed_id)

            if p.initial_assessed and p.orders_1_done and p.orders_2_done:
                stab = disp.stabilization_draw()
                self.eventlog.add(self.env.now, "stabilization_start", pid=p.id, area=area_name, bed=bed_id, minutes=stab)
                yield self.env.timeout(stab)

                if random.random() < consults.request_prob:
                    svc = random.randint(1, consults.service_count)
                    p.consult_service = svc
                    self.eventlog.add(self.env.now, "consult_requested", pid=p.id, area=area_name, bed=bed_id, service=svc)
                    yield self.env.timeout(u(10, 60))
                    self.eventlog.add(self.env.now, "consult_attended", pid=p.id, area=area_name, bed=bed_id, service=svc)
                    if random.random() < consults.admit_prob_by_service(svc):
                        if caps.transfer_only_admit:
                            t_transfer = caps.admit_transfer_total_time_draw()
                            p.admitted = True
                            self.eventlog.add(self.env.now, "admit_transfer_start", pid=p.id, area=area_name, bed=bed_id, minutes=t_transfer)
                            yield self.env.timeout(t_transfer)
                            self.eventlog.add(self.env.now, "admit_transfer_complete", pid=p.id)
                            p.disposition_time = self.env.now; break
                        else:
                            board = consults.local_boarding_time_draw()
                            p.admitted = True; p.boarding_start = self.env.now
                            self.eventlog.add(self.env.now, "boarding_start", pid=p.id, area=area_name, bed=bed_id, minutes=board)
                            yield self.env.timeout(board)
                            self.eventlog.add(self.env.now, "inpatient_transfer", pid=p.id, area=area_name, bed=bed_id)
                            p.disposition_time = self.env.now; break
                    else:
                        buf = disp.post_discharge_buffer_draw()
                        self.eventlog.add(self.env.now, "discharge_buffer_start", pid=p.id, area=area_name, bed=bed_id, minutes=buf)
                        yield self.env.timeout(buf)
                        self.eventlog.add(self.env.now, "discharged", pid=p.id, area=area_name, bed=bed_id)
                        p.disposition_time = self.env.now; break
                else:
                    buf = disp.post_discharge_buffer_draw()
                    self.eventlog.add(self.env.now, "discharge_buffer_start", pid=p.id, area=area_name, bed=bed_id, minutes=buf)
                    yield self.env.timeout(buf)
                    self.eventlog.add(self.env.now, "discharged", pid=p.id, area=area_name, bed=bed_id)
                    p.disposition_time = self.env.now; break
            yield self.env.timeout(5)

        self.bed_pid[area_name][bed_id] = None
        area.beds_in_use -= 1
        self.eventlog.add(self.env.now, "bed_out", pid=p.id, area=area_name, bed=bed_id)

# =========================
# FastTrack wrapper (FIFO)
# =========================

class FTPhysician:
    def __init__(self, name, start_minute, max_new_signups, assess_time1=31, assess_time2=40):
        self.name = name
        self.start_minute = start_minute
        self.max_new_signups = max_new_signups
        self.signup_log = {}
        self.assess_time1 = assess_time1
        self.assess_time2 = assess_time2
        self.resource = None
    def can_accept(self, current_minute):
        day = current_minute // (24*60)
        day_minute = current_minute % (24*60)
        hour_index = (day_minute - self.start_minute) // 60
        if hour_index < 0 or hour_index >= len(self.max_new_signups): return False
        key = (day, hour_index)
        return self.signup_log.get(key, 0) < self.max_new_signups[hour_index]
    def register_patient(self, current_minute):
        day = current_minute // (24*60)
        day_minute = current_minute % (24*60)
        hour_index = (day_minute - self.start_minute) // 60
        if hour_index < 0 or hour_index >= len(self.max_new_signups): return
        key = (day, hour_index)
        self.signup_log[key] = self.signup_log.get(key, 0) + 1

def _ft_log_patient(p: Patient):
    return {
        "pid": p.id, "path":"fasttrack", "name": f"FT_{p.id}",
        "arrival": p.arrival_time, "assess1_time": getattr(p, "assess1_time", None),
        "assess2_time": getattr(p, "assess2_time", None),
        "lwbs": getattr(p, "lwbs_true", False),
        "lab_ordered": getattr(p, "req_lab", False),
        "lab_start_time": getattr(p, "lab_start_time", None),
        "lab_end_time": getattr(p, "lab_end_time", None),
        "di_ordered": getattr(p, "req_diagnostic", False),
        "di_type": getattr(p, "diagnostic_type", None),
        "di_start_time": getattr(p, "di_start_time", None),
        "di_end_time": getattr(p, "di_end_time", None),
    }

class FastTrackRuntime:
    """Wrapper that reuses FIFO intake logic with shared env/eventlog."""
    def __init__(self, env, eventlog, assessment_spaces_amount, physicians: List[FTPhysician],
                 lab_time_dist, di_time_dist_map, long_treatment_time_dist, lwbs_threshold_dist):
        self.env = env; self.eventlog = eventlog
        self.assessment_spaces = simpy.Resource(env, capacity=assessment_spaces_amount)
        self.waiting_queue = deque(); self.reassess_queue = deque()
        self.physicians = physicians
        for phys in self.physicians:
            phys.resource = simpy.Resource(env, capacity=1)
        self.lab_time_dist = lab_time_dist
        self.di_time_dist_map = di_time_dist_map
        self.long_treatment_time_dist = long_treatment_time_dist
        self.lwbs_threshold_dist = lwbs_threshold_dist
        self.results = []

    def add_walkin(self, patient: Patient):
        # Set FT-specific flags similar to FIFO Patient
        patient.path = "fasttrack"
        patient.assess1_req = True
        patient.req_lab = (random.random() < 0.55)
        di_probs_local = {'ultrasound': 0.10, 'CT': 0.1448, 'Xray': 0.2976}
        rnd, cum = random.random(), 0
        patient.req_diagnostic = False; patient.diagnostic_type = None
        for k, p in di_probs_local.items():
            cum += p
            if rnd < cum:
                patient.req_diagnostic = True; patient.diagnostic_type = k; break
        patient.assess2_req = patient.req_lab or patient.req_diagnostic
        patient.long_treatment = patient.req_lab and patient.req_diagnostic and patient.assess2_req and (random.random() < 0.04)

        # attach distributions
        patient.LAB_TIME_DIST = self.lab_time_dist
        patient.DI_TIME_DIST_MAP = self.di_time_dist_map
        patient.LONG_TREATMENT_TIME_DIST = self.long_treatment_time_dist
        patient.LWBS_THRESHOLD_DIST = self.lwbs_threshold_dist

        # launch
        self.env.process(self._patient_process(patient))

    def _patient_process(self, patient: Patient):
        env = self.env
        yield env.timeout(random.randint(0, 10))
        patient.time_wait_lwbs = patient.LWBS_THRESHOLD_DIST()
        if patient.long_treatment:
            patient.long_treatment_time = patient.LONG_TREATMENT_TIME_DIST()
        arrival_time = env.now
        self.eventlog.add(env.now, "ft_arrival", pid=patient.id, area=patient.area)
        self.waiting_queue.append((arrival_time, patient))

        while True:
            if getattr(patient, "lwbs_true", False) or getattr(patient, "processed", False):
                return

            # LWBS pre-assessment
            if (env.now - arrival_time) > patient.time_wait_lwbs and not getattr(patient, "assess1_complete", False):
                self.waiting_queue = deque([(t,p) for t,p in self.waiting_queue if p.id != patient.id])
                self.reassess_queue = deque([(t,p) for t,p in self.reassess_queue if p.id != patient.id])
                patient.lwbs_true = True
                self.eventlog.add(env.now, "lwbs", pid=patient.id, path="fasttrack")
                self.results.append(_ft_log_patient(patient))
                return

            # Reassess
            if self.reassess_queue and self.assessment_spaces.count < self.assessment_spaces.capacity:
                _, rp = self.reassess_queue.popleft()
                if getattr(rp, "lwbs_true", False) or getattr(rp, "processed", False): continue
                with self.assessment_spaces.request() as req:
                    yield req
                    rp.assess2_time = env.now
                    rp.assess2_phys = rp.assess1_phys
                    phys = rp.assess2_phys
                    yield env.timeout(max(1, phys.assess_time2 + random.randint(-20, 20)))
                    rp.assess2_complete = True
                    if rp.long_treatment:
                        yield env.timeout(rp.long_treatment_time)
                    self.eventlog.add(env.now, "ft_reassess_done", pid=rp.id)
                    self.results.append(_ft_log_patient(rp))
                    rp.processed = True
                    continue

            # Initial assessment
            elif self.waiting_queue and self.assessment_spaces.count < self.assessment_spaces.capacity:
                _, npat = self.waiting_queue.popleft()
                if getattr(npat, "lwbs_true", False) or not getattr(npat, "assess1_req", True) or getattr(npat, "processed", False):
                    continue
                with self.assessment_spaces.request() as req:
                    result = yield req | env.timeout(npat.time_wait_lwbs)
                    if req not in result:
                        npat.lwbs_true = True
                        self.eventlog.add(env.now, "lwbs", pid=npat.id, path="fasttrack_wait_assess")
                        self.results.append(_ft_log_patient(npat))
                        npat.processed = True; return

                    # find FT physician
                    wait_start = env.now; phys = None
                    while env.now - wait_start < npat.time_wait_lwbs:
                        for cand in self.physicians:
                            if cand.can_accept(env.now):
                                reqp = cand.resource.request(); yield reqp
                                cand.register_patient(env.now); phys = cand; break
                        if phys: break
                        yield env.timeout(1)
                    if not phys:
                        npat.lwbs_true = True
                        self.eventlog.add(env.now, "lwbs", pid=npat.id, path="fasttrack_no_phys")
                        self.results.append(_ft_log_patient(npat))
                        npat.processed = True; return

                    # assess
                    npat.assess1_phys = phys
                    npat.assess1_time = env.now
                    self.eventlog.add(env.now, "ft_assess_start", pid=npat.id, doctor=phys.name)
                    with phys.resource.request() as reqp:
                        yield reqp
                        yield env.timeout(max(1, phys.assess_time1 + random.randint(-20, 20)))
                    self.eventlog.add(env.now, "ft_assess_done", pid=npat.id, doctor=phys.name)
                    npat.assess1_complete = True

                    # lab
                    if getattr(npat, "req_lab", False):
                        lt = npat.LAB_TIME_DIST()
                        npat.lab_start_time = env.now
                        self.eventlog.add(env.now, "ft_lab_start", pid=npat.id)
                        yield env.timeout(lt)
                        npat.lab_end_time = env.now
                        self.eventlog.add(env.now, "ft_lab_done", pid=npat.id)

                    # DI
                    if getattr(npat, "req_diagnostic", False):
                        di_t = npat.DI_TIME_DIST_MAP[npat.diagnostic_type]()
                        npat.di_start_time = env.now
                        self.eventlog.add(env.now, "ft_di_start", pid=npat.id, modality=npat.diagnostic_type)
                        yield env.timeout(di_t)
                        npat.di_end_time = env.now
                        self.eventlog.add(env.now, "ft_di_done", pid=npat.id, modality=npat.diagnostic_type)

                    if getattr(npat, "assess2_req", False):
                        self.reassess_queue.append((env.now, npat))
                    else:
                        self.results.append(_ft_log_patient(npat))
                        npat.processed = True
                        self.eventlog.add(env.now, "ft_discharge", pid=npat.id)
                        return
            yield env.timeout(1)

    def to_dataframe(self):
        return pd.DataFrame(self.results)

# =========================
# Combined orchestrator
# =========================

class CombinedSim:
    def __init__(self, env, eventlog,
                 acute_core: AcuteCore,
                 fasttrack: FastTrackRuntime,
                 triage_weights: TriageWeights,
                 lwbs_draw: Callable[[], float],
                 walkin_hourly_lambda: List[float],
                 p_fasttrack: float,
                 sim_minutes: Optional[int],
                 tail_minutes: int):
        self.env = env; self.eventlog = eventlog
        self.acute = acute_core; self.fasttrack = fasttrack
        self.tw = triage_weights; self.lwbs_draw = lwbs_draw
        self.walkin_hourly_lambda = walkin_hourly_lambda
        self.p_fasttrack = p_fasttrack
        if sim_minutes is not None:
            self.end_time = sim_minutes
        else:
            self.end_time = len(walkin_hourly_lambda)*60 + tail_minutes
        self.env.process(self._walkin_router())

    def _walkin_router(self):
        area_names = list(self.acute.areas.keys())
        hours = len(self.walkin_hourly_lambda)
        for h in range(hours):
            k = np.random.poisson(self.walkin_hourly_lambda[h % len(self.walkin_hourly_lambda)])
            offsets = sorted(np.random.randint(0, 60, size=k).tolist())
            for off in offsets:
                yield self.env.timeout(max(0, off - (self.env.now % 60)))
                # build a patient, then route
                area = random.choice(area_names)
                p = Patient(self.env, area, self.eventlog, self.tw, self.lwbs_draw, ctas=None)
                if random.random() < self.p_fasttrack:
                    p.path = "fasttrack"
                    self.eventlog.add(self.env.now, "triage_route", pid=p.id, route="fasttrack", area=area)
                    self.fasttrack.add_walkin(p)
                else:
                    p.path = "acute"
                    self.eventlog.add(self.env.now, "triage_route", pid=p.id, route="acute", area=area)
                    self.acute.add_acute_walkin(area, p)
            if self.env.now % 60 != 0:
                yield self.env.timeout(60 - (self.env.now % 60))

    def run(self, until: Optional[float] = None):
        self.env.run(until=until if until is not None else self.end_time)

# =========================
# Example: build & run
# =========================

if __name__ == "__main__":
    random.seed(7); np.random.seed(7)

    sim_cfg = SimConfig(
        areas = {
            "A": AreaConfig(name="A", beds=10, nurse_model=NurseModelConfig(model="ratio", ratio=2, lab_support=True)),
            "B": AreaConfig(name="B", beds=10, nurse_model=NurseModelConfig(model="team", team_nurses=3, lab_support=False)),
        },
        doctors = [
            DoctorConfig(name="DrA1", area="A", start_minute=8*60, shift_minutes=10*60,
                         hourly_max_signups=[3,3,2,2,2,1,1,1,1,1], max_active_panel=8),
            DoctorConfig(name="DrB1", area="B", start_minute=8*60, shift_minutes=12*60,
                         hourly_max_signups=[4,3,3,2,2,2,1,1,1,1,1,1], max_active_panel=9),
        ],
        arrivals = ArrivalsConfig(
            hours=12,
            walkin_hourly_lambda=[6,8,10,12,14,16,18,16,14,12,10,8],
            lwbs_threshold_draw=lambda: u(60, 240)
        ),
        ems = EMSConfig(
            enabled=True,
            internal_generation=True,
            hours=12,
            hourly_lambda=[2,3,4,5,6,7,7,6,5,4,3,2],
            ctas_mix={1:0.03, 2:0.12, 3:0.45, 4:0.35, 5:0.05},
            p_critical=0.01,
            p_direct_to_bed=0.30,
            download_capacity=12,
            offload_service_time_draw=lambda: np.random.uniform(8, 18),
            offload_nurses_per_hour=[1,1,2,2,3,3,3,3,2,2,1,1],
            crew_hospital_time_draw=lambda: 25.0
        ),
        triage_weights = TriageWeights(),
        orders = OrdersConfig(),
        consults = ConsultConfig(),
        disposition = DispositionConfig(),
        capabilities = CapabilitiesConfig(
            has_Xray=True, has_CT=False, has_US=True,
            transfer_only_admit=False,
            external_di_roundtrip=True,
            external_di_total_time_draw=lambda: u(100, 180),
            admit_transfer_total_time_draw=lambda: u(90, 180)
        ),
        sim_minutes = 12*60 + 240,  # 12h arrivals + 4h tail
        tail_minutes = 240
    )

    # Shared infra
    env = simpy.Environment()
    eventlog = EventLog()

    # Acute core (uses shared env/log)
    acute_core = AcuteCore(env=env, eventlog=eventlog, cfg=sim_cfg)

    # FastTrack runtime (simple FIFO intake docs)
    ft_physicians = [
        FTPhysician("FT_Doc1", start_minute=8*60, max_new_signups=[6,6,5,5,4,3,3,3,2,2,1,1]),
    ]
    fasttrack = FastTrackRuntime(
        env=env, eventlog=eventlog, assessment_spaces_amount=6,
        physicians=ft_physicians,
        lab_time_dist=lambda: np.random.uniform(20, 60),
        di_time_dist_map={"ultrasound": lambda: np.random.uniform(30, 90),
                          "CT": lambda: np.random.uniform(35, 70),
                          "Xray": lambda: np.random.uniform(15, 40)},
        long_treatment_time_dist=lambda: np.random.uniform(30, 120),
        lwbs_threshold_dist=lambda: np.random.uniform(30, 120)
    )

    # Combined orchestrator (routes walk-ins between FT and Acute)
    combined = CombinedSim(
        env=env, eventlog=eventlog,
        acute_core=acute_core, fasttrack=fasttrack,
        triage_weights=sim_cfg.triage_weights,
        lwbs_draw=sim_cfg.arrivals.lwbs_threshold_draw,
        walkin_hourly_lambda=sim_cfg.arrivals.walkin_hourly_lambda,
        p_fasttrack=0.40,  # 40% of walk-ins to FastTrack
        sim_minutes=sim_cfg.sim_minutes,
        tail_minutes=sim_cfg.tail_minutes
    )

    # Run once (single env)
    combined.run()

    # Outputs
    events_df = eventlog.to_df()

    acute_patients_df = acute_core.results_patients_df()
    ft_patients_df = fasttrack.to_dataframe()

    # Normalize/align fasttrack patient columns to match acute
    if not ft_patients_df.empty:
        ft_patients_df = ft_patients_df.rename(columns={
            "name": "ft_name"
        })
        ft_patients_df["area"] = ft_patients_df.get("area", None)
        ft_patients_df["bed"] = None
        ft_patients_df["ctas"] = None
        ft_patients_df["admitted"] = False
        ft_patients_df["disposition_time"] = None
        ft_patients_df["los_minutes"] = None
        ft_patients_df["initial_assessed"] = ft_patients_df["assess1_time"].notna()
        ft_patients_df["orders1_done"] = True
        ft_patients_df["orders2_done"] = True
        ft_patients_df["consult_service"] = None
        ft_patients_df["acuity"] = None

        ft_patients_df = ft_patients_df[[
            "pid","path","area","bed","arrival","ctas","lwbs","admitted",
            "disposition_time","los_minutes","initial_assessed","orders1_done",
            "orders2_done","consult_service","acuity","ft_name",
            "assess1_time","assess2_time","lab_ordered","lab_start_time","lab_end_time",
            "di_ordered","di_type","di_start_time","di_end_time"
        ]]

    # Assemble unified patient list
    patients_all_df = pd.concat([
        acute_patients_df.assign(ft_name=None, assess1_time=None, assess2_time=None,
                                 lab_ordered=None, lab_start_time=None, lab_end_time=None,
                                 di_ordered=None, di_type=None, di_start_time=None, di_end_time=None),
        ft_patients_df
    ], ignore_index=True, sort=False)

    # Preview
    print("\n=== Patients (combined, head) ===")
    print(patients_all_df.head(10))
    print("\n=== Events (head) ===")
    print(events_df.head(10))
