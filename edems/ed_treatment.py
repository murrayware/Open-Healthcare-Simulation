from __future__ import annotations

import random

import simpy
import simpy.events as sim_events


class EDTreatmentMixin:
    """Nursing, labs, DI, and in-bed treatment flows."""

    def _eff_acuity(self, p) -> float:
        a = float(getattr(p, "acuity", 0.0) or 0.0)
        b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)
        return a + b

    def _maybe_stabilize(self, p, area):
        if not getattr(p, "requires_stabilization", 0):
            return

        if getattr(p, "stabilization_done", 0):
            return

        stab_draw = getattr(
            getattr(self.cfg, "disposition", None), "stabilization_draw", None
        )
        if not callable(stab_draw):
            return

        stab_min = float(stab_draw())
        if stab_min <= 0:
            return

        self.eventlog.add(
            self.env.now, "stabilization_start", pid=p.id, area=area, minutes=stab_min
        )
        yield self.env.timeout(stab_min)
        self.eventlog.add(self.env.now, "stabilization_end", pid=p.id, area=area)
        p.stabilization_done = 1

    def _init_nurses(self):
        """
        Acute-only nursing models:
          • ratio: create K nurse panels (capacity=1)
          • team: single pooled resource(capacity=team_nurses)
        """
        self._nurse_mode = {}
        self._nurse_team_pool = {}
        self._nurse_ratio_panels = {}

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
                r = max(1, int(nm.ratio or 1))
                beds = int(self._cap.get(area, 0))
                panels = max(1, beds // r)
                self._nurse_mode[area] = "ratio"
                self._nurse_ratio_panels[area] = [
                    simpy.Resource(self.env, capacity=1) for _ in range(panels)
                ]
            else:
                self._nurse_mode[area] = "off"

    def _nurse_assess_minutes(self, p) -> float:
        a = max(0.0, min(2.5, float(getattr(p, "acuity", 0.0))))
        target = 5.0 + (a / 2.5) * (120.0 - 5.0)
        lo = max(5.0, 0.75 * target)
        hi = min(120.0, 1.25 * target)
        return random.uniform(lo, hi)

    def _get_nurse_req(self, p, area: str):
        mode = self._nurse_mode.get(area, "off")
        if mode == "team":
            return self._nurse_team_pool[area].request()
        elif mode == "ratio":
            panels = self._nurse_ratio_panels.get(area, [])
            if not panels:
                return None
            idx = p.id % len(panels)
            return panels[idx].request()
        return None

    def _treat_acute_with_assigned_doctor(self, p, area: str, doc):
        """Run acute care with a pre-assigned doctor."""
        try:
            # Touch 1
            assess_min = self.docmgr.assess_minutes(doc)
            self.eventlog.add(
                self.env.now,
                "assess_start",
                pid=p.id,
                area=area,
                minutes=assess_min,
                mode="ACUTE",
                doctor=doc["name"],
                touch=1,
            )
            yield self.env.timeout(assess_min)
            p.treatment_start = self.env.now
            self.eventlog.add(
                self.env.now,
                "assess_end",
                pid=p.id,
                area=area,
                mode="ACUTE",
                doctor=doc["name"],
                touch=1,
            )

            # Consult / admit before the rest of work, matching your current flow
            if area != self._ft_name and (
                getattr(p, "two_touch", 0) == 1 or getattr(p, "three_touch", 0) == 1
            ):
                want_consult = random.random() < float(
                    getattr(self.cfg.orders, "consult_prob", 0.30) or 0.30
                )
                if want_consult:
                    service = yield from self._run_consults_if_applicable(p)
                    yield from self._maybe_stabilize(p, area)
                    if service is not None:
                        yield from self._admit_to_inpatient(p, service, area, doc)
                        return
                else:
                    p.consult_ordered = 0

            # Nursing + labs
            nurse_req = self._get_nurse_req(p, area)
            nurse_minutes = self._nurse_assess_minutes(p)
            if nurse_req is not None:
                with nurse_req as nr:
                    yield nr
                    p.nurse_assess_start = self.env.now
                    self.eventlog.add(
                        self.env.now,
                        "nurse_assess_start",
                        pid=p.id,
                        area=area,
                        minutes=nurse_minutes,
                    )
                    procs = [self.env.timeout(nurse_minutes)]
                    if getattr(p, "requires_lab", 0) == 1:
                        procs.append(self.env.process(self._run_labs(p)))
                    yield (
                        procs[0]
                        if len(procs) == 1
                        else sim_events.AllOf(self.env, procs)
                    )
                    p.nurse_assess_end = self.env.now
                    p.nurse_assess_minutes = p.nurse_assess_end - p.nurse_assess_start
                    self.eventlog.add(
                        self.env.now,
                        "nurse_assess_end",
                        pid=p.id,
                        minutes=p.nurse_assess_minutes,
                    )
            else:
                if getattr(p, "requires_lab", 0) == 1:
                    yield from self._run_labs(p)

            # DI
            if getattr(p, "requires_di", 0) == 1:
                yield from self._run_di(p)

            # Reassess touch 2
            rmin2 = self.docmgr.reassess_minutes(doc)
            self.eventlog.add(
                self.env.now,
                "reassess_start",
                pid=p.id,
                area=area,
                minutes=rmin2,
                mode="ACUTE",
                doctor=doc["name"],
                touch=2,
            )
            yield self.env.timeout(rmin2)
            self.eventlog.add(
                self.env.now,
                "reassess_end",
                pid=p.id,
                area=area,
                mode="ACUTE",
                doctor=doc["name"],
                touch=2,
            )

            # Reassess touch 3
            if getattr(p, "three_touch", 0) == 1:
                rmin3 = self.docmgr.reassess_minutes(doc)
                self.eventlog.add(
                    self.env.now,
                    "reassess_start",
                    pid=p.id,
                    area=area,
                    minutes=rmin3,
                    mode="ACUTE",
                    doctor=doc["name"],
                    touch=3,
                )
                yield self.env.timeout(rmin3)
                self.eventlog.add(
                    self.env.now,
                    "reassess_end",
                    pid=p.id,
                    area=area,
                    mode="ACUTE",
                    doctor=doc["name"],
                    touch=3,
                )

            # Core treatment
            treat_min = random.randint(10, 30)
            yield self.env.timeout(treat_min)

            # Discharge path
            yield from self._maybe_stabilize(p, area)
            self._discharge_from_ed(p, area, doc, area_busy_attr="_busy")

        finally:
            self.docmgr.release_panel(doc)
            self.eventlog.add(
                self.env.now,
                "doctor_panel_release",
                pid=p.id,
                area=area,
                mode="ACUTE",
                doctor=doc["name"],
                doc_active_panel=doc["active_panel"],
            )

    def _treat_fast_with_assigned_doctor(self, p, area: str, doc):
        assert doc is not None, (
            "FAST: _treat_fast_with_assigned_doctor expects a pre-booked doc"
        )

        assess_min = self.docmgr.assess_minutes(doc)
        self.eventlog.add(
            self.env.now,
            "assess_start",
            pid=p.id,
            area=area,
            minutes=assess_min,
            mode="FAST",
            doctor=doc["name"],
        )
        yield self.env.timeout(assess_min)
        p.treatment_start = self.env.now
        self.eventlog.add(
            self.env.now,
            "assess_end",
            pid=p.id,
            area=area,
            mode="FAST",
            doctor=doc["name"],
        )

        procs = []
        if getattr(p, "requires_lab", 0) == 1:
            procs.append(self.env.process(self._run_labs(p)))
        if getattr(p, "requires_di", 0) == 1:
            procs.append(self.env.process(self._run_di(p)))
        if procs:
            yield sim_events.AllOf(self.env, procs)

        if getattr(p, "one_touch", 0) == 1:
            treat_min = random.randint(120, 240)
            yield self.env.timeout(treat_min)
        else:
            rmin = self.docmgr.reassess_minutes(doc)
            self.eventlog.add(
                self.env.now,
                "reassess_start",
                pid=p.id,
                area=area,
                minutes=rmin,
                mode="FAST",
                doctor=doc["name"],
                touch=2,
            )
            yield self.env.timeout(rmin)
            self.eventlog.add(
                self.env.now,
                "reassess_end",
                pid=p.id,
                area=area,
                mode="FAST",
                doctor=doc["name"],
                touch=2,
            )
            treat_min = random.randint(120, 240)
            yield self.env.timeout(treat_min)

        yield from self._maybe_stabilize(p, area)
        self._discharge_from_ed(p, area, doc, area_busy_attr="_ft_busy")

        self.docmgr.release_panel(doc)
        self.eventlog.add(
            self.env.now,
            "doctor_panel_release",
            pid=p.id,
            area=area,
            mode="FAST",
            doctor=doc["name"],
            doc_active_panel=doc["active_panel"],
        )
