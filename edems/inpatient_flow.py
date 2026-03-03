# edems/inpatient_flow.py
from __future__ import annotations
from collections import deque
from typing import Dict, Deque, Optional

import simpy

class InpatientFlowMixin:
    """
    Inpatient admission + boarding logic.
    - When a consult decides 'admit', call: self._admit_request(p, service_name)
    - Patient holds ED bed until transfer ('boarding').
    - Inpatient unit has finite beds and waitlist; LOS runs on the unit bed.
    """

    def _init_inpatient(self):
        self._units: Dict[str, dict] = {}
        self._unit_cap: Dict[str, int] = {}
        self._unit_busy: Dict[str, int] = {}
        self._unit_wait: Dict[str, Deque[int]] = {}
        self._unit_los_draw: Dict[str, callable] = {}

        inp = getattr(self.cfg, "inpatient", None)
        if not inp or not getattr(inp, "units", None):
            # no inpatient modeling configured
            return

        for name, spec in inp.units.items():
            self._units[name] = spec
            cap = int(getattr(spec, "beds", 0) or 0)
            self._unit_cap[name] = cap
            self._unit_busy[name] = 0
            self._unit_wait[name] = deque()
            self._unit_los_draw[name] = getattr(spec, "los_draw")

    # --- external entry point from consult logic ---
    def _admit_request(self, p, service_name: str):
        """Call when consult decides to admit. Chooses a unit, queues or starts stay."""
        svc_to_unit = getattr(self.cfg.inpatient, "service_to_unit", None)
        unit_name = service_name
        if callable(svc_to_unit):
            try:
                unit_name = svc_to_unit(service_name)
            except Exception:
                unit_name = service_name

        if unit_name not in self._unit_cap:
            # If inpatient not configured, degrade gracefully (treat as discharge)
            self.eventlog.add(self.env.now, "admit_failed_no_unit",
                              pid=p.id, service=service_name, unit=unit_name)
            return

        # mark decision + fields
        p.admit = 1
        p.admit_service = service_name
        p.admit_unit = unit_name
        p.admit_decision_time = self.env.now
        p.emergency_inpatient_time = None  # set at transfer
        p.inpatient_start = None
        p.inpatient_end = None
        p.inpatient_los_minutes = None

        self.eventlog.add(self.env.now, "admit_decision",
                          pid=p.id, service=service_name, unit=unit_name,
                          unit_busy=self._unit_busy[unit_name], unit_cap=self._unit_cap[unit_name])

        # try to place now; otherwise waitlist (patient keeps ED bed busy)
        if self._unit_busy[unit_name] < self._unit_cap[unit_name]:
            self._start_inpatient_stay(p, unit_name)
        else:
            # create an event the ED flow can wait on (optional)
            p._admit_event = getattr(p, "_admit_event", simpy.Event(self.env))
            self._unit_wait[unit_name].append(p.id)
            self.eventlog.add(self.env.now, "admit_waitlist_enqueue",
                              pid=p.id, unit=unit_name, qlen=len(self._unit_wait[unit_name]))

    def _try_place_inpatient_from_waitlist(self, unit_name: str):
        """Called after a unit bed frees; pulls the next ED-boarder if present."""
        if self._unit_busy[unit_name] >= self._unit_cap[unit_name]:
            return
        q = self._unit_wait[unit_name]
        while q and self._unit_busy[unit_name] < self._unit_cap[unit_name]:
            pid = q.popleft()
            p = self.patients.get(pid)
            if not p or getattr(p, "inpatient_start", None) is not None:
                continue
            self._start_inpatient_stay(p, unit_name)

    def _start_inpatient_stay(self, p, unit_name: str):
        """Transfers patient to unit and runs their inpatient LOS."""
        # mark inpatient start, compute ED boarding time
        p.inpatient_start = self.env.now
        if getattr(p, "admit_decision_time", None) is not None:
            p.emergency_inpatient_time = p.inpatient_start - p.admit_decision_time

        # free ED bed now (transfer out of ED)
        self._free_ed_bed_on_transfer(p)

        # occupy unit bed
        self._unit_busy[unit_name] += 1
        self.eventlog.add(self.env.now, "admit_transfer",
                          pid=p.id, unit=unit_name,
                          unit_busy=self._unit_busy[unit_name], unit_cap=self._unit_cap[unit_name],
                          emer_inpatient_min=p.emergency_inpatient_time)

        # run inpatient LOS
        los_draw = self._unit_los_draw[unit_name]
        try:
            los_min = float(los_draw())
        except Exception:
            los_min = 24*60.0  # safe fallback: 1 day
        p.inpatient_los_minutes = los_min

        def _inpatient_proc():
            yield self.env.timeout(los_min)
            p.inpatient_end = self.env.now
            self.eventlog.add(self.env.now, "inpatient_discharge",
                              pid=p.id, unit=unit_name, los_min=los_min)
            # free unit bed and backfill from waitlist
            self._unit_busy[unit_name] = max(0, self._unit_busy[unit_name]-1)
            self._try_place_inpatient_from_waitlist(unit_name)

        self.env.process(_inpatient_proc())

    def _free_ed_bed_on_transfer(self, p):
        """Releases the correct ED bed counter when the patient leaves ED for the unit."""
        area = getattr(p, "area", None)
        if area == getattr(self, "_ft_name", None):
            # Fast Track bed
            if hasattr(self, "_ft_busy"):
                self._ft_busy = max(0, self._ft_busy - 1)
                self.eventlog.add(self.env.now, "ft_bed_release_on_transfer",
                                  pid=p.id, busy=self._ft_busy, cap=self._ft_cap)
        else:
            # ACUTE bed
            if area in getattr(self, "_busy", {}):
                self._busy[area] = max(0, self._busy[area] - 1)
                self.eventlog.add(self.env.now, "acute_bed_release_on_transfer",
                                  pid=p.id, area=area, busy=self._busy[area], cap=self._cap.get(area, 0))
