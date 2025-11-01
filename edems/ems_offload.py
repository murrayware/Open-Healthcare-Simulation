# edems/ems_offload.py
from __future__ import annotations
from typing import Optional
import simpy

from .utils import u  # fallback draw

try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from .ed import SingleSiteSim
        from .patient_generation import Patient
except Exception:
    TYPE_CHECKING = False


class EMSOffloadMixin:
    """EMS offload + download capacity + crew-clear timing."""
    # (unchanged content below)
    def _offload_staff_for_hour(self, hour_idx: int) -> int:
        arr = self.cfg.ems.offload_nurses_per_hour
        assert len(arr) == 24, "ems.offload_nurses_per_hour must have length 24 (one day)."
        return int(arr[hour_idx % 24])

    def _offload_staff_scheduler(self):
        hour = 0
        while True:
            target = self._offload_staff_for_hour(hour)
            current = int(self._offload_tokens.level)
            delta = target - current
            if delta > 0:
                yield self._offload_tokens.put(delta)
            elif delta < 0:
                yield self._offload_tokens.get(-delta)
            self.eventlog.add(self.env.now, "offload_staff_set",
                              hour=(hour % 24), day=hour // 24, nurses=target)
            rem = (60 - (self.env.now % 60)) if (self.env.now % 60) != 0 else 60
            yield self.env.timeout(rem)
            hour += 1

    def _ems_offload(self, p: "Patient"):
        yield self._offload_tokens.get(1)
        try:
            p.offload_start = self.env.now
            p.arrival_to_offload = p.offload_start - p.arrival_time
            self.eventlog.add(self.env.now, "offload_start", pid=p.id,
                              arrival_to_offload=p.arrival_to_offload)
            dur: Optional[float] = None
            try:
                if hasattr(self.cfg.ems, "offload_service_time_draw") and callable(self.cfg.ems.offload_service_time_draw):
                    dur = float(self.cfg.ems.offload_service_time_draw())
            except Exception:
                dur = None
            if dur is None:
                dur = u(5, 10)
            yield self.env.timeout(dur)
            p.offload_end = self.env.now
            p.arrival_to_offload = p.offload_end - p.arrival_time
            self.eventlog.add(self.env.now, "offload_end", pid=p.id, duration=dur)
        finally:
            yield self._offload_tokens.put(1)

        wants_download = p.ems_direct or p.is_critical
        if wants_download and self._download_busy < self._download_cap:
            self._place_into_download(p)
            self.env.process(self._ems_clear_after_offload(p))
        elif wants_download and self._download_busy >= self._download_cap:
            if p.is_critical:
                self._download_wait.append(p.id)
                self.eventlog.add(self.env.now, "download_wait", pid=p.id, waitlen=len(self._download_wait))
                self.env.process(self._ems_clear_after_offload(p))
            else:
                self.acute_q.append(p.id)
                self.eventlog.add(self.env.now, "enqueue", pid=p.id, queue="ACUTE",
                                  qlen=len(self.acute_q), area=p.area, is_ems=True, ems_direct=False)
                self.env.process(self._lwbs_watch(p, is_fast=False))
                self.env.process(self._ems_clear_after_offload(p))
        else:
            self.acute_q.append(p.id)
            self.eventlog.add(self.env.now, "enqueue", pid=p.id, queue="ACUTE",
                              qlen=len(self.acute_q), area=p.area, is_ems=True, ems_direct=False)
            self.env.process(self._lwbs_watch(p, is_fast=False))
            self.env.process(self._ems_clear_after_offload(p))

    def _place_into_download(self, p: "Patient"):
        self._download_busy += 1
        p.download_start = self.env.now
        p.acuity_bonus += 0.4
        self.eventlog.add(self.env.now, "download_start", pid=p.id,
                          busy=self._download_busy, cap=self._download_cap)
        self.acute_q.append(p.id)
        self.eventlog.add(self.env.now, "enqueue", pid=p.id, queue="ACUTE",
                          qlen=len(self.acute_q), area=p.area, is_ems=True, ems_direct=True)

    def _ems_clear_after_offload(self, p: "Patient"):
        if p.is_critical and p.download_start is None:
            while p.download_start is None:
                yield self.env.timeout(1)
        dur: Optional[float] = None
        try:
            if hasattr(self.cfg.ems, "crew_hospital_time_draw") and callable(self.cfg.ems.crew_hospital_time_draw):
                dur = float(self.cfg.ems.crew_hospital_time_draw())
        except Exception:
            dur = None
        if dur is None:
            dur = 42.5
        yield self.env.timeout(dur)
        p.ems_clear_time = self.env.now
        if p.offload_end is not None:
            p.offload_to_clear_minutes = p.ems_clear_time - p.offload_end
        p.ems_total_minutes = p.ems_clear_time - p.arrival_time
        self.eventlog.add(self.env.now, "ems_clear", pid=p.id,
                          offload_to_clear=p.offload_to_clear_minutes, total=p.ems_total_minutes)
