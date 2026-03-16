from __future__ import annotations

import random
from typing import Any


class EDSeeder:
    """
    Seed a SingleSiteSim from patient snapshot records.

    Expected patient records look like:

    {
        "loc": "edw" | "eda" | "edf",
        "wait_time": 100,          # minutes in waiting room, only for edw
        "bed_time": 45,            # minutes in bed, only for eda/edf
        "touches": 0 | 1 | 2 | 3,  # doctor touches already completed
        "consult_wait": -1 | 0 | 100,
        "consult_service": None | "Medicine" | "FamilyMed" | "ICU",
        "lab_time": -1 | int,      # minutes since lab was ordered/pending
        "di_time": -1 | int,       # minutes since DI was ordered/pending
        "di_modality": None | "Xray" | "CT" | "US",
        "eip_time": -1 | int,      # minutes boarded / EIP already accumulated
        "acute_area": None | "A" | "B",
        "doctor_name": None | "DrA_06",
        "ctas": None | 1..5,
        "is_ems": False,
    }

    Location codes:
      edw = ED waiting room
      eda = ED acute bed
      edf = ED fast-track bed
    """

    def __init__(self, sim: Any):
        self.sim = sim

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def seed(self, seed_patients: list[dict[str, Any]]) -> None:
        """Seed from a list of patient records."""
        for rec in seed_patients:
            self._seed_one(rec)

    # Backward-compat alias
    def seed_state(self, seed_patients: list[dict[str, Any]]) -> None:
        self.seed(seed_patients)

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _seed_one(self, rec: dict[str, Any]) -> None:
        sim = self.sim
        now = sim.env.now

        loc = rec.get("loc")
        if loc not in {"edw", "eda", "edf"}:
            raise ValueError(f"Unknown seed location: {loc!r}")

        ctas = rec.get("ctas")
        is_ems = bool(rec.get("is_ems", False))

        p = sim._make_patient(ctas=ctas, is_ems=is_ems)
        p.seeded = True

        # _make_patient auto-enqueues; clear that so the seed controls state exactly
        self._remove_from_all_queues(p.id)

        # Clear any pre-existing state we do not want from auto-generation
        p.disp_name = None
        p.bed_start = None
        p.bed_end = None
        p.disposition_time = None
        p.los_minutes = None
        p.treatment_start = None
        p.doctor_name = None

        # Clear / reset workflow-ish fields that we'll override if provided
        p.consult_ordered = 0
        p.consult_start = None
        p.consult_end = None
        p.consult_minutes = None
        p.consult_count = 0
        p.consult_minutes_total = 0.0
        p.consult_admit = 0
        p.consult_units = []

        p.requires_lab = 0
        p.lab_start = None
        p.lab_end = None
        p.lab_minutes = None

        p.requires_di = 0
        p.di_modality = None
        p.di_start = None
        p.di_end = None
        p.di_minutes = None

        p.admit = 0
        p.admit_service = None
        p.admit_unit = None
        p.admit_decision_time = None
        p.emergency_inpatient_time = None
        p.inpatient_start = None

        # ------------------------------------------------------------------
        # Waiting room
        # ------------------------------------------------------------------
        if loc == "edw":
            wait_time = self._coerce_nonneg(rec.get("wait_time", 0.0))
            p.arrival_time = now - wait_time

            # Generic waiting room defaults to acute queue.
            # If you later want fast waiting, add an explicit field like queue="FAST".
            acute_area = rec.get("acute_area")
            if acute_area in getattr(sim, "_cap", {}):
                p.area = acute_area
            else:
                p.area = sim._choose_acute_area_name()

            sim.acute_q.append(p.id)

        # ------------------------------------------------------------------
        # Acute bed
        # ------------------------------------------------------------------
        elif loc == "eda":
            area = rec.get("acute_area")
            if area not in getattr(sim, "_cap", {}):
                area = self._pick_acute_area_with_capacity()

            if area is None:
                # No bed available; skip this seeded patient silently
                return

            sim._busy[area] += 1

            bed_time = self._coerce_nonneg(rec.get("bed_time", 0.0))
            p.area = area
            p.bed_start = now - bed_time
            p.arrival_time = p.bed_start - self._default_pre_bed_wait(p, loc="eda")

            self._assign_bedded_progress(p, rec, loc="eda")

        # ------------------------------------------------------------------
        # Fast-track bed
        # ------------------------------------------------------------------
        elif loc == "edf":
            if sim._ft_busy >= sim._ft_cap:
                return

            sim._ft_busy += 1

            bed_time = self._coerce_nonneg(rec.get("bed_time", 0.0))
            p.area = sim._ft_name
            p.bed_start = now - bed_time
            p.arrival_time = p.bed_start - self._default_pre_bed_wait(p, loc="edf")

            self._assign_bedded_progress(p, rec, loc="edf")

        # ------------------------------------------------------------------
        # Pending consult
        # ------------------------------------------------------------------
        consult_wait = rec.get("consult_wait", -1)
        consult_service = self._normalize_service(rec.get("consult_service"))

        if consult_wait is not None and consult_wait != -1:
            consult_wait = self._coerce_nonneg(consult_wait)
            p.consult_ordered = 1
            p.consult_start = now - consult_wait
            p.consult_end = None
            p.consult_minutes = consult_wait
            p.consult_count = 1
            p.consult_minutes_total = float(consult_wait)

            if consult_service is not None:
                p.consult_units = [consult_service]
                p.admit_service = consult_service

        # ------------------------------------------------------------------
        # Pending lab
        # ------------------------------------------------------------------
        lab_time = rec.get("lab_time", -1)
        if lab_time is not None and lab_time != -1:
            lab_time = self._coerce_nonneg(lab_time)
            p.requires_lab = 1
            p.lab_start = now - lab_time
            p.lab_end = None
            p.lab_minutes = lab_time

        # ------------------------------------------------------------------
        # Pending DI
        # ------------------------------------------------------------------
        di_time = rec.get("di_time", -1)
        if di_time is not None and di_time != -1:
            di_time = self._coerce_nonneg(di_time)
            p.requires_di = 1
            p.di_modality = rec.get("di_modality") or self._default_di_modality()
            p.di_start = now - di_time
            p.di_end = None
            p.di_minutes = di_time

        # ------------------------------------------------------------------
        # Boarded / EIP
        # ------------------------------------------------------------------
        eip_time = rec.get("eip_time", -1)
        if eip_time is not None and eip_time != -1:
            eip_time = self._coerce_nonneg(eip_time)
            p.admit = 1
            p.disp_name = "admit"
            p.admit_decision_time = now - eip_time
            p.emergency_inpatient_time = eip_time

            if p.admit_service is None:
                p.admit_service = consult_service or self._normalize_service(rec.get("admit_service")) or "Medicine"

        sim.eventlog.add(
            sim.env.now,
            "seed_patient",
            pid=p.id,
            location=loc,
            area=p.area,
            touches=getattr(rec, "touches", rec.get("touches", 0)),
        )

    # ------------------------------------------------------------------
    # State logic
    # ------------------------------------------------------------------

    def _assign_bedded_progress(self, p: Any, rec: dict[str, Any], loc: str) -> None:
        """
        Assign realistic in-bed progress:
        - touches already done
        - doctor name
        - treatment_start if already seen
        """
        bed_time = self._coerce_nonneg(rec.get("bed_time", 0.0))
        touches = int(rec.get("touches", 0) or 0)

        p.one_touch = 0
        p.two_touch = 0
        p.three_touch = 0
        p.touch_assigned = touches
        p.touch_effective = touches

        if touches <= 0:
            # waiting in bed, not yet seen
            p.treatment_start = None
        else:
            if touches == 1:
                p.one_touch = 1
            elif touches == 2:
                p.two_touch = 1
            else:
                p.three_touch = 1

            # assign a doctor name if one not explicitly supplied
            p.doctor_name = rec.get("doctor_name") or self._choose_doctor_name_for_area(p.area)

            # assume first doctor contact happened a little after bed placement
            first_contact_delay = min(max(1.0, 0.15 * bed_time), max(1.0, bed_time - 1.0))
            p.treatment_start = p.bed_start + first_contact_delay

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _remove_from_all_queues(self, pid: int) -> None:
        sim = self.sim
        try:
            sim.fasttrack_q.remove(pid)
        except Exception:
            pass
        try:
            sim.acute_q.remove(pid)
        except Exception:
            pass
        try:
            sim._download_wait.remove(pid)
        except Exception:
            pass

    def _pick_acute_area_with_capacity(self) -> str | None:
        sim = self.sim
        choices = []
        for area in getattr(sim, "_cap", {}):
            if sim._busy.get(area, 0) < sim._cap.get(area, 0):
                choices.append(area)
        if not choices:
            return None
        return random.choice(choices)

    def _choose_doctor_name_for_area(self, area: str) -> str | None:
        cfg_doctors = getattr(self.sim.cfg, "doctors", []) or []
        names = [d.name for d in cfg_doctors if getattr(d, "area", None) == area]
        if not names:
            return None
        return random.choice(names)

    def _normalize_service(self, svc: Any) -> str | None:
        if svc in (None, "", 0):
            return None

        s = str(svc).strip()
        if not s:
            return None

        # Match against configured inpatient services case-insensitively
        units = getattr(getattr(self.sim.cfg, "inpatient", None), "units", {}) or {}
        for name in units.keys():
            if str(name).lower() == s.lower():
                return str(name)

        # fallback title case
        return s

    def _default_pre_bed_wait(self, p: Any, loc: str) -> float:
        # These are just snapshot defaults so arrival_time < bed_start
        if loc == "edf":
            return random.uniform(5, 20)
        return random.uniform(10, 45)

    def _default_di_modality(self) -> str:
        di_map = getattr(getattr(self.sim.cfg, "orders", None), "di_time_draw_map", {}) or {}
        keys = list(di_map.keys())
        if not keys:
            return "Xray"
        return random.choice(keys)

    @staticmethod
    def _coerce_nonneg(x: Any) -> float:
        if x is None:
            return 0.0
        return max(0.0, float(x))
