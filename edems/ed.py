# edems/ed.py
from __future__ import annotations
import simpy
from collections import deque
from typing import Dict, Optional, List

from .eventlog import EventLog
from .policies import ArrivalPolicy, EMSArrivalPolicy

from .ems_offload import EMSOffloadMixin
from .ed_treatment import EDTreatmentMixin
from .patient_generation import PatientGenerationMixin
from .lwbs import LwbsMixin
from .orders import OrdersMixin
from .inpatient_flow import InpatientFlowMixin
from .doctor import DoctorManager

try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from .patient_generation import Patient
except Exception:
    TYPE_CHECKING = False


class SingleSiteSim(EMSOffloadMixin, EDTreatmentMixin, PatientGenerationMixin, LwbsMixin, OrdersMixin, InpatientFlowMixin,  DoctorManager):
    def __init__(self, cfg, external_env=None, external_eventlog=None):
        self.cfg = cfg
        self.env = external_env or simpy.Environment()
        self.eventlog = external_eventlog or EventLog()

        # --- storage & queues ---
        self.patients = {}
        self.fasttrack_q = deque()
        self.acute_q = deque()
        # Inpatient state:
        self._init_inpatient()

        # --- ACUTE areas ---
        self._areas = list(getattr(self.cfg, "areas", {}).keys())
        self._cap   = {a: self.cfg.areas[a].beds for a in self._areas}
        self._busy  = {a: 0 for a in self._areas}

        # --- FAST TRACK state (must be set before _init_doctors) ---
        ft_cfg = getattr(self.cfg, "fasttrack", None)
        self._ft_enabled = bool(ft_cfg and getattr(ft_cfg, "enabled", False))
        self._ft_name    = getattr(ft_cfg, "name", "FAST") if self._ft_enabled else "FAST"
        self._ft_cap     = int(getattr(ft_cfg, "assessment_spaces", 0) or 0)
        self._ft_busy    = 0

        ft_cfg = getattr(self.cfg, "fasttrack", None)
        self._ft_enabled: bool = bool(ft_cfg and getattr(ft_cfg, "enabled", False))
        self._ft_name: str = getattr(ft_cfg, "name", "FAST") if self._ft_enabled else "FAST"
        self._ft_cap: int = int(getattr(ft_cfg, "assessment_spaces", 0) or 0)
        self._ft_busy: int = 0

        # ---- Doctor manager ----
        areas_needed = list(self._cap.keys())
        if self._ft_enabled and self._ft_cap > 0:
            areas_needed.append(self._ft_name)

        self.docmgr = DoctorManager(self.env, self.eventlog, host=self)


        # --- EMS download holding ---
        self._download_cap  = int(getattr(self.cfg.ems, "download_capacity", 0) or 0)
        self._download_busy = 0
        self._download_wait = deque()
        self._init_nurses()

        # init orders (lab prob etc.)
        self._init_orders()

        # --- Offload nurse tokens (24h profile repeats) ---
        assert len(getattr(self.cfg.ems, "offload_nurses_per_hour", [])) == 24, \
            "ems.offload_nurses_per_hour must have length 24 (one day)."
        self._offload_tokens = simpy.Container(self.env, init=self._offload_staff_for_hour(0), capacity=9999)
        self.env.process(self._offload_staff_scheduler())

        # --- Start arrival policies ---
        self.arrivals = ArrivalPolicy(cfg)
        self.arrivals.start(self.env, make_patient_cb=self._make_patient)

        if getattr(self.cfg, "ems", None) and getattr(self.cfg.ems, "enabled", False) and getattr(self.cfg.ems, "internal_generation", True):
            self.ems_arrivals = EMSArrivalPolicy(cfg)
            self.ems_arrivals.start(self.env, make_patient_cb=self._make_patient)

        # --- Start dispatchers ---
        self.env.process(self._acute_bed_dispatcher())
        if self._ft_enabled and self._ft_cap > 0:
            self.env.process(self._fasttrack_bed_dispatcher())



    def results(self):
        import pandas as pd
        rows = []
        for p in self.patients.values():
            rows.append({
                "pid": p.id, "area": p.area, "arrival": p.arrival_time,
                "ctas": p.ctas, "acuity": p.acuity, "is_ems": p.is_ems,
                "is_critical": p.is_critical, "lwbs_min": p.lwbs_threshold,
                "lwbs": p.lwbs, "arrival_to_offload": p.arrival_to_offload,
                "offload_to_clear": p.offload_to_clear_minutes,
                "ems_total_minutes": p.ems_total_minutes,
                "download_minutes": p.download_minutes,
                "bed_start": p.bed_start, "bed_end": p.bed_end,
                "disposition_time": p.disposition_time, "los_minutes": p.los_minutes,
                "doctor": p.doctor_name,
                "treatment_start": p.treatment_start,
                "requires_lab": p.requires_lab,
                "requires_lab": p.requires_lab,
                "requires_di": p.requires_di,
                "di_modality": p.di_modality,
                "requires_lab": p.requires_lab,
                "lab_start": p.lab_start, "lab_end": p.lab_end, "lab_minutes": p.lab_minutes,
                "lab_is_critical": p.lab_is_critical,
                "requires_di": p.requires_di,
                "di_modality": p.di_modality,
                "di_start": p.di_start, "di_end": p.di_end, "di_minutes": p.di_minutes,
                "nurse_assess_start": p.nurse_assess_start,
                "nurse_assess_end": p.nurse_assess_end,
                "nurse_assess_minutes": p.nurse_assess_minutes,
                "one_touch": p.one_touch,
                "two_touch": p.two_touch,
                "three_touch": p.three_touch,
                "consult_ordered": p.consult_ordered,
                "consult_minutes": p.consult_minutes,
                "consult_ordered": getattr(p, "consult_ordered", 0),
                "consult_count": getattr(p, "consult_count", 0),
                "consult_minutes_total": getattr(p, "consult_minutes_total", 0.0),
                "consult_admit": getattr(p, "consult_admit", 0),
                "admit_unit": getattr(p, "admit_unit", None),
                # Optional: stringify consulted units list
                "consult_units": ",".join(getattr(p, "consult_units", [])) if getattr(p, "consult_units", None) else "",
                #inpatient
                "admit": getattr(p, "admit", 0),
                "admit_service": getattr(p, "admit_service", None),
                "admit_unit": getattr(p, "admit_unit", None),
                "admit_decision_time": getattr(p, "admit_decision_time", None),
                "emergency_inpatient_time": getattr(p, "emergency_inpatient_time", None),
                "inpatient_start": getattr(p, "inpatient_start", None),
                "inpatient_end": getattr(p, "inpatient_end", None),
                "inpatient_los_minutes": getattr(p, "inpatient_los_minutes", None),
                    }
                    )


        patients_df = pd.DataFrame(rows).sort_values("pid").reset_index(drop=True)
        events_df = self.eventlog.to_df()
        return patients_df, events_df

