from __future__ import annotations

import random


class EDDispositionMixin:
    """Consult/admit logic and final ED disposition."""

    def _run_consults_if_applicable(self, p):
        """
        Up to 2 sequential consults for ACUTE + (two_touch or three_touch).
        If admitted, returns the service/unit name. Otherwise returns None.
        """
        if p.area == getattr(self, "_ft_name", "FAST"):
            return None

        if not (getattr(p, "two_touch", 0) == 1 or getattr(p, "three_touch", 0) == 1):
            return None

        inpatient_cfg = getattr(self.cfg, "inpatient", None)
        if not inpatient_cfg or not getattr(inpatient_cfg, "units", None):
            return None

        units = inpatient_cfg.units
        choices = []
        weights = []

        for name, spec in units.items():
            cp = float(getattr(spec, "consult_p", 0.0) or 0.0)
            if cp > 0:
                choices.append((name, spec))
                weights.append(cp)

        if not choices:
            return None

        total = sum(weights)
        weights = [w / total for w in weights]

        if not hasattr(p, "consult_ordered"):
            p.consult_ordered = 0
        if not hasattr(p, "consult_count"):
            p.consult_count = 0
        if not hasattr(p, "consult_minutes_total"):
            p.consult_minutes_total = 0.0
        if not hasattr(p, "consult_admit"):
            p.consult_admit = 0
        if not hasattr(p, "consult_units"):
            p.consult_units = []

        def pick_unit():
            r = random.random()
            acc = 0.0
            for (name, spec), w in zip(choices, weights):
                acc += w
                if r <= acc:
                    return name, spec
            return choices[-1]

        for attempt in (1, 2):
            unit_name, spec = pick_unit()
            p.consult_ordered = 1
            p.consult_count += 1
            p.consult_units.append(unit_name)

            tdraw = getattr(spec, "consult_time_draw", None)
            cmin = float(tdraw()) if callable(tdraw) else 100.0

            self.eventlog.add(
                self.env.now,
                "consult_start",
                pid=p.id,
                area=p.area,
                unit=unit_name,
                attempt=attempt,
                minutes=cmin,
            )
            yield self.env.timeout(cmin)
            self.eventlog.add(
                self.env.now,
                "consult_end",
                pid=p.id,
                area=p.area,
                unit=unit_name,
                attempt=attempt,
            )

            p.consult_minutes_total += cmin

            cap = float(getattr(spec, "consult_admit_p", 0.0) or 0.0)
            if random.random() < cap:
                p.consult_admit = 1
                p.admit_unit = unit_name
                self.eventlog.add(
                    self.env.now,
                    "consult_admit",
                    pid=p.id,
                    area=p.area,
                    unit=unit_name,
                    attempt=attempt,
                )
                return unit_name
            else:
                self.eventlog.add(
                    self.env.now,
                    "consult_no_admit",
                    pid=p.id,
                    area=p.area,
                    unit=unit_name,
                    attempt=attempt,
                )

        p.consult_admit = 0
        return None

    def _admit_to_inpatient(self, p, service: str, area: str, doc):
        """
        Minimal bridge to inpatient.
        Preferred path:
            self.hospital.inpatient.admit(...)
        Fallback path:
            old EIP timeout if hospital/inpatient not wired yet.
        """
        p.consult_admit = 1
        p.admit = 1
        p.disp_name = "admit"
        p.admit_service = service
        p.admit_decision_time = self.env.now

        self.eventlog.add(
            self.env.now,
            "admit_decision",
            pid=p.id,
            area=area,
            service=service,
            doctor=doc["name"],
            admit_decision_time=p.admit_decision_time,
        )

        # Real inpatient system, if present
        if hasattr(self, "hospital") and getattr(self.hospital, "inpatient", None):
            self.eventlog.add(
                self.env.now,
                "admit_requested",
                pid=p.id,
                service=service,
                unit=service,
            )

            yield from self.hospital.inpatient.admit(p, service)

            p.inpatient_start = self.env.now
            p.bed_end = p.inpatient_start
            p.disposition_time = p.bed_end
            p.los_minutes = p.disposition_time - p.arrival_time

            if area in self._busy:
                self._busy[area] = max(0, self._busy[area] - 1)

            self.eventlog.add(
                self.env.now,
                "admit_transfer_complete",
                pid=p.id,
                area=area,
                is_ems=p.is_ems,
                doctor=doc["name"],
            )
            return

        # Fallback to old EIP behavior
        units = getattr(getattr(self.cfg, "inpatient", None), "units", {}) or {}
        spec = units.get(service)
        eip_draw = getattr(spec, "eip_time", None) if spec else None

        if callable(eip_draw):
            eip_min = float(eip_draw())
        else:
            eip_min = 180.0

        p.emergency_inpatient_time = eip_min

        self.eventlog.add(
            self.env.now,
            "boarding_start",
            pid=p.id,
            area=area,
            service=service,
            doctor=doc["name"],
            eip_minutes=eip_min,
        )
        yield self.env.timeout(eip_min)

        p.inpatient_start = self.env.now
        p.bed_end = p.inpatient_start
        p.disposition_time = p.bed_end
        p.los_minutes = p.disposition_time - p.arrival_time

        if area in self._busy:
            self._busy[area] = max(0, self._busy[area] - 1)

        self.eventlog.add(
            self.env.now,
            "admit_transfer_complete",
            pid=p.id,
            area=area,
            is_ems=p.is_ems,
            doctor=doc["name"],
            eip_minutes=p.emergency_inpatient_time,
        )

    def _discharge_from_ed(self, p, area: str, doc, area_busy_attr: str = "_busy"):
        p.bed_end = self.env.now
        p.disposition_time = self.env.now
        p.los_minutes = p.disposition_time - p.arrival_time
        p.disp_name = "discharge"

        self.eventlog.add(
            self.env.now,
            "bed_end",
            pid=p.id,
            area=area,
            is_ems=p.is_ems,
            doctor=doc["name"],
        )

        if area_busy_attr == "_ft_busy":
            self._ft_busy = max(0, self._ft_busy - 1)
            busy = self._ft_busy
            cap = self._ft_cap
        else:
            self._busy[area] = max(0, self._busy[area] - 1)
            busy = self._busy[area]
            cap = self._cap[area]

        self.eventlog.add(
            self.env.now,
            "discharge",
            pid=p.id,
            area=area,
            busy=busy,
            cap=cap,
            is_ems=p.is_ems,
            doctor=doc["name"],
        )
