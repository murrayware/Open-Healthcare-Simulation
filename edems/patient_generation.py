# edems/patient_generation.py
from __future__ import annotations
import random

try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from .ed import SingleSiteSim
except Exception:
    TYPE_CHECKING = False


class Patient:
    _id = 0

    def __init__(self, env, area_name, eventlog, triage_w, lwbs_draw, *,
                 ctas: int | None = None, is_ems: bool = False,
                 ems_direct: bool = False, is_critical: bool = False):
        Patient._id += 1
        self.id = Patient._id
        self.env = env
        self.area = area_name  # initial area assignment ("FAST" or an acute label like "A")
        self.eventlog = eventlog
        self.is_ems = bool(is_ems)
        self.ems_direct = bool(ems_direct)   # intended for download after offload
        self.is_critical = bool(is_critical)

        # --- triage features (same as before) ---
        self.age = random.randint(18, 95)
        self.temp = random.uniform(36.0, 40.5)
        self.o2   = random.uniform(80, 100)
        self.bp   = random.uniform(70, 180)
        self.gcs  = random.randint(3, 15)
        self.complaint = random.randint(1, 168)
        self.is_trauma = (random.random() < 0.10)
        self.is_mh     = (random.random() < 0.12)
        self.ctas = ctas if ctas else 3
        self.doctor_name = None
        self.treatment_start = None

        # --- acuity score (unchanged formula) ---
        w = triage_w
        flags = int(self.is_trauma) + int(self.is_mh)
        self.acuity = (
            w.w_age*(self.age/100.0) +
            w.w_temp*((self.temp-36.0)/4.5) +
            w.w_o2*((100-self.o2)/20.0) +
            w.w_bp*((120-self.bp)/50.0) +
            w.w_gcs*((15-self.gcs)/12.0) +
            w.w_complaint*(self.complaint/168.0) +
            w.w_flags*flags +
            w.ctas_bonus.get(self.ctas, 0.0)
        )
        self.acuity_bonus = 0.0  # e.g., EMS download bump

        # --- LWBS threshold (minutes), set at arrival & weighted by acuity ---
        base = float(lwbs_draw())  # treat draw as a mean-like baseline in minutes
        self.lwbs_threshold = self._calc_lwbs_threshold_minutes(base, self.acuity)
        self.lwbs = 0  # 1 if patient leaves without being seen


        # Nursing assessment (acute only)
        self.nurse_assess_start = None
        self.nurse_assess_end = None
        self.nurse_assess_minutes = None

        # Timestamps
        self.arrival_time = env.now
        self.bed_start = None
        self.bed_end = None
        self.disposition_time = None
        self.los_minutes = None

        # EMS offload timestamps and metrics
        self.offload_start = None
        self.offload_end = None
        self.arrival_to_offload = None

        # EMS crew clear metrics
        self.ems_clear_time = None
        self.offload_to_clear_minutes = None
        self.ems_total_minutes = None  # arrival -> clear

        # EMS download/offload holding area timestamps
        self.download_start = None
        self.download_end = None
        self.download_minutes = None

        #Orders Area
        self.requires_lab = 0
        self.requires_di = 0
        self.di_modality = None          # "Xray" | "CT" | "US" | None
        self.requires_lab = 0
        self.lab_start = None
        self.lab_end = None
        self.lab_minutes = None
        self.lab_is_critical = 0
        # DI flags/timestamps
        self.requires_di = 0
        self.di_modality = None
        self.di_start = None
        self.di_end = None
        self.di_minutes = None
        #Doctor touchpoints
        self.one_touch = 0
        self.two_touch = 0
        self.three_touch = 0
        #consults
        self.consult_ordered = 0
        self.consult_start = None
        self.consult_end = None
        self.consult_minutes = None


        eventlog.add(env.now, "arrival", pid=self.id, area=self.area, acuity=self.acuity,
                     ctas=self.ctas, is_ems=self.is_ems, is_critical=self.is_critical)
        eventlog.add(env.now, "lwbs_set", pid=self.id, lwbs_min=self.lwbs_threshold,
                     base_min=base, area=self.area, is_ems=self.is_ems)

    @staticmethod
    def _calc_lwbs_threshold_minutes(base_min: float, acuity: float) -> float:
        # Soft normalization (assume most acuity in 0..2.5 range)
        a = max(0.0, min(2.5, float(acuity)))
        norm = a / 2.5
        scale = 1.4 - 0.8 * norm  # linear taper
        return max(5.0, base_min * scale)




class PatientGenerationMixin:
    """Creation & initial routing for walk-ins and EMS, plus basic validation."""



    def _assign_touches_and_route(self, p, is_fast_candidate: bool):
        """
        Decide 1/2/3 touches at *generation*, force 3-touch to ACUTE, and (for now)
        TREAT 3-touch AS 2-touch while remembering it was originally 3-touch.
        Returns final is_fast (possibly overridden).
        """
        p1, p2, p3 = self._touch_probs()
        r = random.random()
        if r < p1:
            assigned = 1
        elif r < p1 + p2:
            assigned = 2
        else:
            assigned = 3

        # record assigned vs effective
        p.touch_assigned = assigned
        p.one_touch = 1 if assigned == 1 else 0
        p.two_touch = 1 if assigned == 2 else 0
        p.three_touch = 1 if assigned == 3 else 0

        # 3-touch patients never FAST; we route to ACUTE and (for now) treat as 2-touch
        if assigned == 3:
            # force ACUTE
            was_fast = is_fast_candidate
            is_fast_candidate = False
            if was_fast:
                # pick an acute area and log the override
                p.area = self._choose_acute_area_name()
                self.eventlog.add(self.env.now, "route_override",
                                  pid=p.id, reason="three_touch_force_acute", new_area=p.area)

            # treat as 2-touch operationally, but remember original for analytics
            p.was_three_touch = 1
            p.two_touch = 1
            p.three_touch = 0
            p.touch_effective = 2
        else:
            p.was_three_touch = 0
            p.touch_effective = assigned

        return is_fast_candidate

  # edems/patient_generation.py

    # ---- creation & arrival intak ----
    def _make_patient(self, ctas=None, is_ems=False, lwbs_draw=None):
        if is_ems:
            # EMS → ACUTE areas by policy
            area_name = self._choose_acute_area_name()
            try:
                ems_direct = (random.random() < float(self.cfg.ems.p_direct_to_bed))
            except Exception:
                ems_direct = False
            try:
                is_critical = (random.random() < float(self.cfg.ems.p_critical))
            except Exception:
                is_critical = False

            p = Patient(
                self.env,
                area_name,
                self.eventlog,
                self.cfg.triage_weights,
                lwbs_draw or self._lwbs_draw_fallback(True),
                ctas=ctas,
                is_ems=True,
                ems_direct=ems_direct,
                is_critical=is_critical,
            )
            self.patients[p.id] = p

            # --- touches belong in patient generation (per your spec) ---
            self._assign_touches(p)

            # --- RESTORED: assign orders-at-arrival here ---
            if hasattr(self, "_orders_on_arrival"):
                self._orders_on_arrival(p)

            # EMS offload process (no FAST routing for EMS right now)
            self.env.process(self._ems_offload(p))
            return p

        # ---- WALK-IN branch ----
        is_fast = self._route_fast_walkin()
        area_name = self._ft_name if is_fast else self._choose_acute_area_name()

        p = Patient(
            self.env,
            area_name,
            self.eventlog,
            self.cfg.triage_weights,
            lwbs_draw or self._lwbs_draw_fallback(False),
            ctas=ctas,
            is_ems=False,
        )
        self.patients[p.id] = p

        # --- touches belong in patient generation (per your spec) ---
        self._assign_touches(p)

        # --- RESTORED: assign orders-at-arrival here ---
        if hasattr(self, "_orders_on_arrival"):
            self._orders_on_arrival(p)

        # 3-touch → force ACUTE (do NOT demote to 2-touch)
        if getattr(p, "three_touch", 0) == 1 and is_fast:
            is_fast = False
            p.area = self._choose_acute_area_name()
            self.eventlog.add(
                self.env.now, "route_override",
                pid=p.id, reason="three_touch_force_acute_reroute", new_area=p.area
            )

        # --- Enqueue to correct area ---
        if is_fast:
            self.fasttrack_q.append(p.id)
            self.eventlog.add(self.env.now, "enqueue", pid=p.id, queue="FAST",
                              qlen=len(self.fasttrack_q), is_ems=False)
            self.eventlog.add(self.env.now, "route", pid=p.id, to="FAST",
                              area=p.area, is_ems=False)
        else:
            self.acute_q.append(p.id)
            self.eventlog.add(self.env.now, "enqueue", pid=p.id, queue="ACUTE",
                              qlen=len(self.acute_q), area=p.area, is_ems=False)
            self.eventlog.add(self.env.now, "route", pid=p.id, to="ACUTE",
                              area=p.area, is_ems=False)

        # Start LWBS timer for walk-ins
        self.env.process(self._lwbs_watch(p, is_fast))
        return p


    # ---- touches helper (lives in patient generation) ----
    def _assign_touches(self, p):
        """Assign one/two/three-touch based on cfg.orders.{p_one_touch,p_three_touch}.
        Two-touch is the complement. Three-touch will flag force_acute."""
        # Defaults if not present
        p1 = float(getattr(self.cfg.orders, "p_one_touch", 0.15) or 0.0)
        p3 = float(getattr(self.cfg.orders, "p_three_touch", 0.10) or 0.0)
        # clamp and normalize if needed
        p1 = max(0.0, min(1.0, p1))
        p3 = max(0.0, min(1.0, p3))
        if p1 + p3 > 1.0:
            scale = 1.0 / (p1 + p3)
            p1 *= scale
            p3 *= scale

        r = random.random()
        if r < p1:
            p.one_touch, p.two_touch, p.three_touch = 1, 0, 0
            touches = 1
        elif r < p1 + p3:
            p.one_touch, p.two_touch, p.three_touch = 0, 0, 1
            p.force_acute = 1  # ensure ACUTE routing for 3-touch
            touches = 3
        else:
            p.one_touch, p.two_touch, p.three_touch = 0, 1, 0
            touches = 2

        self.eventlog.add(self.env.now, "touch_assigned",
                          pid=p.id, one=p.one_touch, two=p.two_touch, three=p.three_touch, chosen=touches)

    # ---- routing helpers ----
    def _choose_acute_area_name(self) -> str:
        import random
        if getattr(self.cfg, "areas", None):
            return random.choice(list(self.cfg.areas.keys()))
        return "ACUTE"

    def _route_fast_walkin(self) -> bool:
        import random
        ft = getattr(self.cfg, "fasttrack", None)
        if not ft or not getattr(ft, "enabled", False):
            return False
        # For walk-ins only (EMS now always ACUTE path post-offload for now)
        if getattr(self.cfg.arrivals, "fasttrack_route_probability", None) is not None:
            p = float(self.cfg.arrivals.fasttrack_route_probability)
        else:
            p = float(getattr(ft, "route_probability", 0.0) or 0.0)
        return (random.random() < p)

    # ---- validation ----
    def _validate_doctors(self) -> None:
        defined_areas = set(getattr(self.cfg, "areas", {}).keys())
        ft_name = getattr(getattr(self.cfg, "fasttrack", None), "name", None)
        for d in getattr(self.cfg, "doctors", []) or []:
            if d.area not in defined_areas and (ft_name is None or d.area != ft_name):
                raise ValueError(
                    f"Doctor '{d.name}' assigned to unknown area '{d.area}'. "
                    f"Known acute areas: {sorted(defined_areas)}"
                )
