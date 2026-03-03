# edems/ed_treatment.py
from __future__ import annotations
from typing import List, Tuple, Dict, Any, Optional
import math
import simpy
import random
import simpy.events as sim_events

try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from .patient_generation import Patient
except Exception:
    pass


class EDTreatmentMixin:
    """Bed dispatchers + doctor assignment + labs-gated treatment for ACUTE and FAST."""

    def _eff_acuity(self, p) -> float:
        a = float(getattr(p, "acuity", 0.0) or 0.0)
        b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)
        return a + b

    def _maybe_stabilize(self, p, area):

        if not getattr(p, "requires_stabilization", 0):
            return

        if getattr(p, "stabilization_done", 0):
            return

        stab_draw = getattr(getattr(self.cfg, "disposition", None), "stabilization_draw", None)
        if not callable(stab_draw):
            return

        stab_min = float(stab_draw())
        if stab_min <= 0:
            return

        self.eventlog.add(self.env.now, "stabilization_start",
                          pid=p.id, area=area, minutes=stab_min)

        yield self.env.timeout(stab_min)

        self.eventlog.add(self.env.now, "stabilization_end",
                          pid=p.id, area=area)

        p.stabilization_done = 1

    def _queue_priority(self, p, area: str, now: float) -> float:
        """
        Priority = base acuity + acuity_bonus
                 + (time_waiting_hours * area_weight * CTAS_multiplier)
                 + optional download_bonus (only for ACUTE).
        All weights default if cfg.queue is absent.
        """
        # base
        base = float(getattr(p, "acuity", 0.0) or 0.0) + float(getattr(p, "acuity_bonus", 0.0) or 0.0)

        # how long waiting (prefer download hold time if in download)
        if self._in_download_now(p):
            waited_min = now - getattr(p, "download_start", now)
            in_download = True
        else:
            waited_min = now - getattr(p, "arrival_time", now)
            in_download = False
        waited_hr = max(0.0, float(waited_min)) / 60.0

        # pull weights safely (works even if cfg.queue doesn't exist)
        qcfg = getattr(self.cfg, "queue", None)
        acute_w = float(getattr(qcfg, "acute_time_weight", 0.8))
        fast_w  = float(getattr(qcfg, "fast_time_weight", 0.35))
        dl_w    = float(getattr(qcfg, "download_wait_weight", 1.2))
        ctas_mults = getattr(qcfg, "ctas_wait_mult", {1: 2.0, 2: 1.6, 3: 1.2, 4: 1.0, 5: 0.8})

        # area-specific time weight
        time_w = fast_w if area == getattr(self, "_ft_name", "FAST") else acute_w

        # CTAS multiplier (boost 1/2/3 more than 4/5)
        ctas = int(getattr(p, "ctas", 3) or 3)
        c_mul = float(ctas_mults.get(ctas, 1.0))

        # optional: extra boost when currently sitting in download (ACUTE only)
        download_bonus = (dl_w * waited_hr) if (in_download and area != getattr(self, "_ft_name", "FAST")) else 0.0

        return base + (time_w * waited_hr * c_mul) + download_bonus



    def _acute_queue_refresher(self):
        while True:
            uniq = []
            seen = set()
            for pid in list(self.acute_q):
                if pid in seen: continue
                p = self.patients.get(pid)
                if p is None: continue
                seen.add(pid); uniq.append(pid)
            uniq.sort(key=lambda pid: (-self._eff_acute_score(self.patients[pid]),
                                       float(getattr(self.patients[pid], "arrival_time", 0.0))))
            try:
                self.acute_q.clear(); self.acute_q.extend(uniq)
            except AttributeError:
                from collections import deque
                self.acute_q = deque(uniq)
            yield self.env.timeout(5)



    def _in_download_now(self, p) -> bool:
        return (getattr(p, "download_start", None) is not None) and (getattr(p, "download_end", None) is None)

    def _acute_rule_bonuses(self, p) -> float:
        # keep these constants the same as your dispatcher
        EMS_CRIT_BONUS = 5.0
        DOWNLOAD_BONUS = 5.0
        bonus = 0.0
        if getattr(p, "is_ems", False) and getattr(p, "is_critical", False):
            bonus += EMS_CRIT_BONUS
        if self._in_download_now(p):
            bonus += DOWNLOAD_BONUS
        return bonus

    def _eff_acute_score(self, p) -> float:
        a = float(getattr(p, "acuity", 0.0) or 0.0)
        b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)  # time-based bonus
        r = self._acute_rule_bonuses(p)                    # rule-based bonuses
        return a + b + r



    def _init_nurses(self):
        """
        Acute-only nursing models:
          • ratio: create K 'nurse panels' (simpy.Resource capacity=1) where K=floor(beds/ratio) or 1 min.
                   Patients are mapped to a panel by a stable hash (pid % K) to emulate fixed nurse groups.
          • team:  single pooled simpy.Resource(capacity=team_nurses).
        """
        import math
        self._nurse_mode = {}             # area -> "ratio" | "team" | "off"
        self._nurse_team_pool = {}        # area -> simpy.Resource (team model)
        self._nurse_ratio_panels = {}     # area -> List[simpy.Resource] (ratio model)

        for area, acfg in self.cfg.areas.items():
            nm = getattr(acfg, "nurse_model", None)
            if not nm:
                self._nurse_mode[area] = "off"
                continue

            if nm.model == "team":
                n = int(nm.team_nurses or 0)
                if n <= 0:
                    self._nurse_mode[area] = "off"
                    continue
                self._nurse_mode[area] = "team"
                self._nurse_team_pool[area] = simpy.Resource(self.env, capacity=n)

            elif nm.model == "ratio":
                r = max(1, int(nm.ratio or 1))          # beds per nurse
                beds = int(self._cap.get(area, 0))
                panels = max(1, beds // r)              # number of nurses from ratio
                self._nurse_mode[area] = "ratio"
                self._nurse_ratio_panels[area] = [simpy.Resource(self.env, capacity=1) for _ in range(panels)]

            else:
                self._nurse_mode[area] = "off"


    #nurse helpers
    def _nurse_assess_minutes(self, p) -> float:
        """
        Scale 5..120 min by acuity (soft-clipped 0..2.5).
        Draw around that target ±25%, clipped to [5,120].
        """
        a = max(0.0, min(2.5, float(getattr(p, "acuity", 0.0))))
        target = 5.0 + (a / 2.5) * (120.0 - 5.0)
        lo = max(5.0, 0.75 * target)
        hi = min(120.0, 1.25 * target)
        import random
        return random.uniform(lo, hi)

    #nurse helpers
    def _get_nurse_req(self, p, area: str):
        """
        Return a context manager (req) to be used as:
            with req as r: yield r
        according to nurse model of area.
        """
        mode = self._nurse_mode.get(area, "off")
        if mode == "team":
            return self._nurse_team_pool[area].request()
        elif mode == "ratio":
            panels = self._nurse_ratio_panels.get(area, [])
            if not panels:
                return None
            idx = p.id % len(panels)  # stable mapping of patient to nurse panel
            return panels[idx].request()
        return None


    @staticmethod
    def _day_anchor(now_min: float) -> int:
        return (int(now_min) // 1440) * 1440

    def _doc_on_shift(self, doc: Dict[str, Any], now_min: float) -> bool:
        """Shifts repeat daily; allows wrap past midnight."""
        day0 = self._day_anchor(now_min)
        s = day0 + doc["start_min"]
        e = s + doc["shift_min"]
        if doc["shift_min"] >= 1440:
            return True
        if e <= day0 + 1440:
            return s <= now_min < e
        # wrapped
        return (now_min >= s) or (now_min < (e - 1440))

    @staticmethod
    def _abs_hour(now_min: float) -> int:
        return int(now_min // 60)

    @staticmethod
    def _hour_of_day(now_min: float) -> int:
        return int((now_min % 1440) // 60)

    def _assign_doctor(self, p, area: str):
        doc = self.docmgr.try_signup(area, self.env.now)
        if not doc:
            return None
        p.doctor_name = doc["name"]
        self.eventlog.add(self.env.now, "doctor_assigned", pid=p.id, area=area,
                          doctor=p.doctor_name, doc_active_panel=doc["active_panel"])
        return doc

    def _release_doctor_panel(self, doc):
        self.docmgr.release_panel(doc)

    def _draw_assess_minutes(self, doc):
        return self.docmgr.assess_minutes(doc)

    def _reassess_minutes(self, doc):
        return self.docmgr.reassess_minutes(doc)

    def _run_consults_if_applicable(self, p) -> None:
        """
        Up to 2 sequential consults for ACUTE + (two_touch or three_touch).
        Each consult: choose a unit weighted by consult_p, wait consult_time_draw,
        then admit with probability consult_admit_p. If admitted, mark and stop.
        """
        # Only for ACUTE area and 2/3-touch patients
        if p.area == getattr(self, "_ft_name", "FAST"):
            return
        if not (getattr(p, "two_touch", 0) == 1 or getattr(p, "three_touch", 0) == 1):
            return

        inpatient_cfg = getattr(self.cfg, "inpatient", None)
        if not inpatient_cfg or not getattr(inpatient_cfg, "units", None):
            return

        units = inpatient_cfg.units  # Dict[str, InpatientUnitSpec]
        # Build weighted list by consult_p (ignore zero/negative)
        choices = []
        weights = []
        for name, spec in units.items():
            cp = float(getattr(spec, "consult_p", 0.0) or 0.0)
            if cp > 0:
                choices.append((name, spec))
                weights.append(cp)

        if not choices:
            return

        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]

        # init patient consult fields if not present
        if not hasattr(p, "consult_ordered"):
            p.consult_ordered = 0
        if not hasattr(p, "consult_count"):
            p.consult_count = 0
        if not hasattr(p, "consult_minutes_total"):
            p.consult_minutes_total = 0.0
        if not hasattr(p, "consult_admit"):
            p.consult_admit = 0
        if not hasattr(p, "consult_units"):
            p.consult_units = []  # list of unit names consulted

        # helper: weighted pick
        def pick_unit() -> tuple[str, object]:
            r = random.random()
            acc = 0.0
            for (name, spec), w in zip(choices, weights):
                acc += w
                if r <= acc:
                    return name, spec
            return choices[-1]  # fallback

        # Up to 2 attempts
        for attempt in (1, 2):
            unit_name, spec = pick_unit()
            p.consult_ordered = 1
            p.consult_count += 1
            p.consult_units.append(unit_name)

            # time draw
            tdraw = getattr(spec, "consult_time_draw", None)
            cmin = float(tdraw()) if callable(tdraw) else 100.0

            self.eventlog.add(self.env.now, "consult_start",
                              pid=p.id, area=p.area, unit=unit_name, attempt=attempt, minutes=cmin)
            yield self.env.timeout(cmin)
            self.eventlog.add(self.env.now, "consult_end",
                              pid=p.id, area=p.area, unit=unit_name, attempt=attempt)

            p.consult_minutes_total += cmin

            # admit test
            cap = float(getattr(spec, "consult_admit_p", 0.0) or 0.0)
            if random.random() < cap:
                p.consult_admit = 1
                p.admit_unit = unit_name
                self.eventlog.add(self.env.now, "consult_admit",
                                  pid=p.id, area=p.area, unit=unit_name, attempt=attempt)
                break
            else:
                self.eventlog.add(self.env.now, "consult_no_admit",
                                  pid=p.id, area=p.area, unit=unit_name, attempt=attempt)
    # ------------------------
    # ACUTE bed dispatcher
    # ------------------------
    from collections import deque

    def _refresh_acute_queue_once(self):
        # Build unique list of valid PIDs
        seen = set()
        uniq = []
        for pid in list(self.acute_q):
            if pid in seen:
                continue
            p = self.patients.get(pid)
            if p is None:
                continue
            seen.add(pid)
            uniq.append(pid)

        # Sort by live score then arrival time
        uniq.sort(key=lambda pid: (-self._eff_acute_score(self.patients[pid]),
                                   float(getattr(self.patients[pid], "arrival_time", 0.0))))

        # Replace queue contents (works for list or deque)
        if hasattr(self.acute_q, "clear") and hasattr(self.acute_q, "extend"):
            self.acute_q.clear()
            self.acute_q.extend(uniq)
        else:
            self.acute_q = deque(uniq)

        # Optional: log a lightweight snapshot for debugging
        try:
            top = uniq[:5]
            snap = [
                dict(pid=pid,
                     score=self._eff_acute_score(self.patients[pid]),
                     acuity=float(getattr(self.patients[pid], "acuity", 0.0) or 0.0),
                     bonus=float(getattr(self.patients[pid], "acuity_bonus", 0.0) or 0.0),
                     rules=self._acute_rule_bonuses(self.patients[pid]))
                for pid in top
            ]
            self.eventlog.add(self.env.now, "acute_queue_refresh", top5=snap, size=len(uniq))
        except Exception:
            pass

    def _acute_queue_refresher(self):
        while True:
            self._refresh_acute_queue_once()
            yield self.env.timeout(5)  # every 5 sim-minutes

    def _acute_bed_dispatcher(self):
        EMS_CRIT_BONUS = 5.0
        DOWNLOAD_BONUS = 5.0  # set to 0.0 if you don't want stacking with EMS_CRIT_BONUS

        while True:
            placed = False

            if self.acute_q:
                cand: List[Tuple[int, str, float, float]] = []
                for pid in list(self.acute_q):
                    p = self.patients.get(pid)
                    if p is None:
                        continue
                    area = p.area
                    if area not in self._cap or self._busy[area] >= self._cap[area]:
                        continue

                    # base + time bonus
                    a = float(getattr(p, "acuity", 0.0) or 0.0)
                    b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)

                    # rule bonuses
                    emscrit = EMS_CRIT_BONUS if (getattr(p, "is_ems", False) and getattr(p, "is_critical", False)) else 0.0
                    dload  = DOWNLOAD_BONUS if self._in_download_now(p) else 0.0
                    score = self._queue_priority(p, area, self.env.now)
                    cand.append((pid, area, score, p.arrival_time))

                    # optional visibility for debugging
                    self.eventlog.add(self.env.now, "dispatch_cand",
                                      pid=pid, area=area,
                                      acuity=a, bonus_time=b,
                                      bonus_emscrit=emscrit, bonus_download=dload,
                                      score=score)

                if cand:
                    cand.sort(key=lambda t: (-t[2], t[3]))
                    pid, area, score, _ = cand[0]

                    # ensure a doctor is available before taking the bed
                    doc = self._assign_doctor(self.patients[pid], area)
                    if doc is None:
                        yield self.env.timeout(1)
                        continue

                    try:
                        self.acute_q.remove(pid)
                    except ValueError:
                        self._release_doctor_panel(doc)
                        yield self.env.timeout(0.1)
                        continue

                    self._busy[area] += 1
                    p = self.patients[pid]
                    p.bed_start = self.env.now

                    # if they were in download, end it & free slot
                    if self._in_download_now(p):
                        p.download_end = self.env.now
                        p.download_minutes = p.download_end - p.download_start
                        self._download_busy = max(0, self._download_busy - 1)
                        self.eventlog.add(self.env.now, "download_end",
                                          pid=pid, minutes=p.download_minutes,
                                          busy=self._download_busy, cap=self._download_cap)

                    # log exactly what drove the pick
                    a = float(getattr(p, "acuity", 0.0) or 0.0)
                    b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)
                    emscrit = EMS_CRIT_BONUS if (getattr(p, "is_ems", False) and getattr(p, "is_critical", False)) else 0.0
                    dload  = DOWNLOAD_BONUS if self._in_download_now(p) else 0.0
                    self.eventlog.add(self.env.now, "bed_start",
                                      pid=pid, area=area,
                                      busy=self._busy[area], cap=self._cap[area],
                                      is_ems=p.is_ems, doctor=p.doctor_name,
                                      chosen_acuity=a, chosen_bonus_time=b,
                                      chosen_bonus_emscrit=emscrit, chosen_bonus_download=dload,
                                      chosen_score=(a + b + emscrit + dload))
                    if p.download_start is not None and p.download_end is None:
                        p.download_end = self.env.now
                        p.download_minutes = p.download_end - p.download_start
                        self._download_busy = max(0, self._download_busy - 1)
                        # make sure dict exists, then pop this patient
                        if hasattr(self, "_download_patients"):
                            self._download_patients.pop(p.id, None)
                        self.eventlog.add(self.env.now, "download_end",
                                          pid=pid, minutes=p.download_minutes,
                                          busy=self._download_busy, cap=self._download_cap)
                        if hasattr(self, "_try_fill_download_from_waitlist"):
                            self._try_fill_download_from_waitlist()

                    # doctor-led flow
                    self.env.process(self._treat_acute_with_assigned_doctor(p, area, doc))
                    placed = True

            yield self.env.timeout(0 if placed else 1)



    def _try_fill_download_from_waitlist(self):
        while self._download_busy < self._download_cap and self._download_wait:
            pid_wait = self._download_wait.popleft()
            p_wait = self.patients.get(pid_wait)
            if p_wait is None or p_wait.download_start is not None:
                continue
            self._place_into_download(p_wait)

    # ------------------------
    # FAST bed dispatcher
    # ------------------------
    def _fasttrack_bed_dispatcher(self):
        while True:
            placed = False
            while self.fasttrack_q and self._ft_busy < self._ft_cap:
                pid = self.fasttrack_q.popleft()
                p = self.patients.get(pid)
                if p is None:
                    continue

                # ensure a doctor available for FAST
                doc = self._assign_doctor(p, self._ft_name)
                if doc is None:
                    # push back & retry
                    self.fasttrack_q.appendleft(pid)
                    yield self.env.timeout(1)
                    continue

                self._ft_busy += 1
                p.bed_start = self.env.now
                self.eventlog.add(self.env.now, "bed_start",
                                  pid=pid, area=self._ft_name,
                                  busy=self._ft_busy, cap=self._ft_cap,
                                  is_ems=p.is_ems, doctor=p.doctor_name)

                self.env.process(self._treat_fast_with_assigned_doctor(p, self._ft_name, doc))
                placed = True

            if not placed:
                yield self.env.timeout(1)
            else:
                yield self.env.timeout(0)

    # ---------------------------------------------
    # Doctor flows (labs AFTER assessment, BEFORE tx)
    # ---------------------------------------------

    def _treat_acute_with_assigned_doctor(self, p, area: str, doc):
        """Run acute care with the doctor already assigned by the dispatcher."""
        try:

            # ---------- Touch 1: initial MD assessment ----------
            assess_min = self.docmgr.assess_minutes(doc)
            self.eventlog.add(self.env.now, "assess_start", pid=p.id, area=area,
                              minutes=assess_min, mode="ACUTE", doctor=doc["name"], touch=1)
            yield self.env.timeout(assess_min)
            p.treatment_start = self.env.now
            self.eventlog.add(self.env.now, "assess_end", pid=p.id, area=area,
                              mode="ACUTE", doctor=doc["name"], touch=1)

            # ---------- Optional consults ----------
            if area != self._ft_name and (getattr(p, "two_touch", 0) == 1 or getattr(p, "three_touch", 0) == 1):
                want_consult = (random.random() < float(getattr(self.cfg.orders, "consult_prob", 0.30) or 0.30))
                if want_consult:
                    p.consult_ordered = 1
                    units = getattr(self.cfg.inpatient, "units", {}) or {}
                    if units:
                        services, weights = [], []
                        for name, spec in units.items():
                            services.append(name)
                            weights.append(float(getattr(spec, "consult_p", 0.0) or 0.0))
                        if sum(weights) <= 0:
                            services, weights = ["Medicine"], [1.0]
                        else:
                            sw = sum(weights); weights = [w / sw for w in weights]
                    else:
                        services, weights = ["Medicine"], [1.0]

                    consult_attempts = 0
                    while consult_attempts < 2:
                        consult_attempts += 1
                        service = random.choices(services, weights=weights, k=1)[0]
                        spec = units.get(service, None)
                        c_draw = getattr(spec, "consult_time_draw", None)
                        c_min = float(c_draw()) if callable(c_draw) else 60.0
                        p.consult_start = self.env.now
                        self.eventlog.add(self.env.now, "consult_start",
                                          pid=p.id, area=area, doctor=doc["name"],
                                          service=service, attempt=consult_attempts)
                        yield self.env.timeout(c_min)
                        p.consult_end = self.env.now
                        p.consult_minutes = p.consult_end - p.consult_start
                        self.eventlog.add(self.env.now, "consult_end",
                                          pid=p.id, area=area, minutes=p.consult_minutes,
                                          service=service, attempt=consult_attempts)

                        admit_p = float(getattr(spec, "consult_admit_p", 0.0) or 0.0)
                        yield from self._maybe_stabilize(p, area)
                        if random.random() < admit_p:
                            # --- Admit decision made right now ---
                            p.consult_admit = 1
                            p.admit = 1
                            p.disp_name = 'admit'
                            p.admit_service = service
                            p.admit_decision_time = self.env.now
                            self.eventlog.add(self.env.now, "admit_decision",
                                              pid=p.id, area=area, service=service, doctor=doc["name"],
                                              admit_decision_time=p.admit_decision_time)

                            # Request inpatient placement (creates/uses p._admit_event)
                            # Request inpatient placement
                            self._admit_request(p, service)
                            self.eventlog.add(self.env.now, "admit_requested",
                                              pid=p.id, service=service,
                                              unit=getattr(p, "admit_unit", None))

                            # --- Admit decision made right now ---
                            p.consult_admit = 1
                            p.admit = 1
                            p.disp_name = 'admit'
                            p.admit_service = service
                            p.admit_decision_time = self.env.now

                            self.eventlog.add(self.env.now, "admit_decision",
                                              pid=p.id, area=area, service=service, doctor=doc["name"],
                                              admit_decision_time=p.admit_decision_time)

                            # NEW: sample EIP from inpatient unit spec
                            eip_draw = getattr(spec, "eip_time", None)

                            if callable(eip_draw):
                                eip_min = float(eip_draw())
                            else:
                                eip_min = 180.0  # fallback default

                            p.emergency_inpatient_time = eip_min

                            # Option A (recommended): boarding consumes ED time (bed stays occupied)
                            self.eventlog.add(self.env.now, "boarding_start",
                                              pid=p.id, area=area, service=service, doctor=doc["name"],
                                              eip_minutes=eip_min)
                            yield self.env.timeout(eip_min)

                            # patient "leaves ED" now
                            p.inpatient_start = self.env.now
                            p.bed_end = p.inpatient_start
                            p.disposition_time = p.bed_end
                            p.los_minutes = p.disposition_time - p.arrival_time

                            if area in self._busy:
                                self._busy[area] = max(0, self._busy[area] - 1)

                            self.eventlog.add(self.env.now, "admit_transfer_complete",
                                              pid=p.id, area=area, is_ems=p.is_ems, doctor=doc["name"],
                                              eip_minutes=p.emergency_inpatient_time)

                            return
                        else:
                            self.eventlog.add(self.env.now, "consult_no_admit", pid=p.id, service=service)


                    p.consult_admit = 0
                else:
                    p.consult_ordered = 0

            # ---------- Nursing assess (+ labs concurrently if nurse present) ----------
            nurse_req = self._get_nurse_req(p, area)
            nurse_minutes = self._nurse_assess_minutes(p)
            if nurse_req is not None:
                with nurse_req as nr:
                    yield nr
                    p.nurse_assess_start = self.env.now
                    self.eventlog.add(self.env.now, "nurse_assess_start", pid=p.id, area=area, minutes=nurse_minutes)
                    procs = [self.env.timeout(nurse_minutes)]
                    if getattr(p, "requires_lab", 0) == 1:
                        procs.append(self.env.process(self._run_labs(p)))
                    yield (procs[0] if len(procs) == 1 else sim_events.AllOf(self.env, procs))
                    p.nurse_assess_end = self.env.now
                    p.nurse_assess_minutes = p.nurse_assess_end - p.nurse_assess_start
                    self.eventlog.add(self.env.now, "nurse_assess_end", pid=p.id, minutes=p.nurse_assess_minutes)
            else:
                if getattr(p, "requires_lab", 0) == 1:
                    yield from self._run_labs(p)

            # ---------- DI (ACUTE) ----------
            if getattr(p, "requires_di", 0) == 1:
                yield from self._run_di(p)

            # ---------- Reassess (touch 2 / 3) ----------
            rmin2 = self.docmgr.reassess_minutes(doc)
            self.eventlog.add(self.env.now, "reassess_start", pid=p.id, area=area,
                              minutes=rmin2, mode="ACUTE", doctor=doc["name"], touch=2)
            yield self.env.timeout(rmin2)
            self.eventlog.add(self.env.now, "reassess_end", pid=p.id, area=area,
                              mode="ACUTE", doctor=doc["name"], touch=2)

            if getattr(p, "three_touch", 0) == 1:
                rmin3 = self.docmgr.reassess_minutes(doc)
                self.eventlog.add(self.env.now, "reassess_start", pid=p.id, area=area,
                                  minutes=rmin3, mode="ACUTE", doctor=doc["name"], touch=3)
                yield self.env.timeout(rmin3)
                self.eventlog.add(self.env.now, "reassess_end", pid=p.id, area=area,
                                  mode="ACUTE", doctor=doc["name"], touch=3)

            # ---------- Core treatment ----------
            TREAT_MIN = random.randint(10,30)
            yield self.env.timeout(TREAT_MIN)

            # ---------- Discharge ----------
            yield from self._maybe_stabilize(p, area)
            p.bed_end = self.env.now
            p.disposition_time = self.env.now
            p.los_minutes = p.disposition_time - p.arrival_time
            p.disp_name = 'discharge'
            self.eventlog.add(self.env.now, "bed_end", pid=p.id, area=area, is_ems=p.is_ems, doctor=doc["name"])
            self._busy[area] = max(0, self._busy[area] - 1)
            self.eventlog.add(self.env.now, "discharge", pid=p.id, area=area,
                              busy=self._busy[area], cap=self._cap[area], is_ems=p.is_ems, doctor=doc["name"])
        finally:
            # always release the same panel we assigned
            self.docmgr.release_panel(doc)
            self.eventlog.add(self.env.now, "doctor_panel_release", pid=p.id, area=area,
                              mode="ACUTE", doctor=doc["name"], doc_active_panel=doc["active_panel"])





    def _treat_fast_with_assigned_doctor(self, p, area: str, doc):

        assert doc is not None, "FAST: _treat_fast_with_assigned_doctor expects a pre-booked doc"

        assess_min = self.docmgr.assess_minutes(doc)
        self.eventlog.add(self.env.now, "assess_start", pid=p.id, area=area,
                          minutes=assess_min, mode="FAST", doctor=doc["name"])
        yield self.env.timeout(assess_min)
        p.treatment_start = self.env.now
        self.eventlog.add(self.env.now, "assess_end", pid=p.id, area=area, mode="FAST", doctor=doc["name"])

        # Labs & DI concurrently (unchanged) ...
        procs = []
        if getattr(p, "requires_lab", 0) == 1:
            procs.append(self.env.process(self._run_labs(p)))
        if getattr(p, "requires_di", 0) == 1:
            procs.append(self.env.process(self._run_di(p)))
        if procs:
            yield sim_events.AllOf(self.env, procs)

        # Touch branching (unchanged, except your random mins are fine)
        if getattr(p, "one_touch", 0) == 1:
            TREAT_MIN = random.randint(120, 240)
            yield self.env.timeout(TREAT_MIN)
        else:
            rmin = self.docmgr.reassess_minutes(doc)
            self.eventlog.add(self.env.now, "reassess_start", pid=p.id, area=area,
                              minutes=rmin, mode="FAST", doctor=doc["name"], touch=2)
            yield self.env.timeout(rmin)
            self.eventlog.add(self.env.now, "reassess_end", pid=p.id, area=area,
                              mode="FAST", doctor=doc["name"], touch=2)
            TREAT_MIN = random.randint(120, 240)
            yield self.env.timeout(TREAT_MIN)

        # Dispo + release (unchanged)
        yield from self._maybe_stabilize(p, area)
        p.bed_end = self.env.now
        p.disposition_time = self.env.now
        p.los_minutes = p.disposition_time - p.arrival_time
        p.disp_name = 'discharge'
        self.eventlog.add(self.env.now, "bed_end", pid=p.id, area=area, is_ems=p.is_ems, doctor=doc["name"])
        self._ft_busy = max(0, self._ft_busy - 1)
        self.eventlog.add(self.env.now, "discharge", pid=p.id, area=area,
                          busy=self._ft_busy, cap=self._ft_cap, is_ems=p.is_ems, doctor=doc["name"])
        self.docmgr.release_panel(doc)
        self.eventlog.add(self.env.now, "doctor_panel_release", pid=p.id, area=area,
                          mode="FAST", doctor=doc["name"], doc_active_panel=doc["active_panel"])
