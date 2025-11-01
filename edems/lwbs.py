# edems/lwbs.py
from __future__ import annotations

try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from .patient_generation import Patient
except Exception:
    pass

class LwbsMixin:
    def _lwbs_draw_fallback(self, is_ems: bool):
        if is_ems and getattr(self.cfg.ems, "lwbs_threshold_draw", None):
            return self.cfg.ems.lwbs_threshold_draw
        return self.cfg.arrivals.lwbs_threshold_draw

    def _lwbs_watch(self, p: "Patient", is_fast: bool):
        yield self.env.timeout(p.lwbs_threshold)

        if p.bed_start is not None:
            return
        if p.is_ems and p.download_start is not None and p.download_end is None:
            return

        removed = False
        if is_fast:
            try:
                self.fasttrack_q.remove(p.id)
                removed = True
                qname = "FAST"
                qlen = len(self.fasttrack_q)
            except ValueError:
                pass
        else:
            try:
                self.acute_q.remove(p.id)
                removed = True
                qname = "ACUTE"
                qlen = len(self.acute_q)
            except ValueError:
                pass

        if removed:
            p.lwbs = 1
            p.disposition_time = self.env.now
            p.los_minutes = (p.disposition_time - p.arrival_time)
            self.eventlog.add(self.env.now, "lwbs",
                              pid=p.id, queue=qname, qlen=qlen,
                              area=p.area, is_ems=p.is_ems)
