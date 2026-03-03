# edems/doctor.py
from __future__ import annotations
from typing import Dict, List, Any, Optional
import math

class DoctorManager:
    def __init__(self, env, eventlog, host):
        self.env = env
        self.eventlog = eventlog
        self.host = host  # SingleSiteSim, used for cfg/areas
        # build by_area from cfg.doctors (same structure you had before)
        self.by_area: Dict[str, List[Dict[str, Any]]] = {}
        for d in (getattr(host.cfg, "doctors", []) or []):
            self.by_area.setdefault(d.area, []).append({
                "name": d.name,
                "area": d.area,
                "start_min": int(d.start_minute),
                "shift_min": int(d.shift_minutes),
                "assess_draw": d.assess_time_draw,
                "reassess_draw": d.reassess_time_draw,
                "max_panel": int(d.max_active_panel),
                "hourly_caps": list(d.hourly_max_signups or []),
                "active_panel": 0,
                "signed_up_by_abs_hour": {},  # abs_hour -> count
            })

    # -------- time helpers ----------
    @staticmethod
    def hour_of_day(now_min: float) -> int:
        return int(now_min // 60) % 24

    @staticmethod
    def abs_hour(now_min: float) -> int:
        return int(now_min // 60)

    def on_shift(self, doc: Dict[str, Any], now_min: float) -> bool:
        start = doc["start_min"]
        dur = doc["shift_min"]
        if dur <= 0:
            return False
        # shifts repeat daily
        day_min = int(now_min) % (24 * 60)
        if start + dur < 24 * 60:
            return start <= day_min < start + dur
        # wrap-around shift
        end = (start + dur) % (24 * 60)
        return (day_min >= start) or (day_min < end)

    def hour_cap(self, doc: Dict[str, Any], now_min: float) -> int:
        caps = doc["hourly_caps"]
        if not caps:
            return math.inf
        idx = self.hour_of_day(now_min)
        return int(caps[idx % len(caps)])

    def can_signup(self, doc: Dict[str, Any], now_min: float) -> bool:
        if not self.on_shift(doc, now_min):
            return False
        if doc["active_panel"] >= doc["max_panel"]:
            return False
        cap = self.hour_cap(doc, now_min)
        signed = doc["signed_up_by_abs_hour"].get(self.abs_hour(now_min), 0)
        return signed < cap

    # -------- selection + booking ----------
    def try_signup(self, area: str, now_min: float) -> Optional[Dict[str, Any]]:
        docs = self.by_area.get(area, [])
        eligible = [d for d in docs if self.can_signup(d, now_min)]
        if not eligible:
            return None
        eligible.sort(key=lambda d: (d["active_panel"], d["name"]))  # least loaded
        doc = eligible[0]
        # book: increment hour counter + panel
        ah = self.abs_hour(now_min)
        doc["signed_up_by_abs_hour"][ah] = doc["signed_up_by_abs_hour"].get(ah, 0) + 1
        doc["active_panel"] += 1
        return doc

    def release_panel(self, doc: Dict[str, Any]) -> None:
        doc["active_panel"] = max(0, doc["active_panel"] - 1)

    # -------- timing draws ----------
    @staticmethod
    def _safe_call(draw, default: float) -> float:
        try:
            return float(draw())
        except Exception:
            return default

    def assess_minutes(self, doc: Dict[str, Any]) -> float:
        return self._safe_call(doc.get("assess_draw"), 15.0)

    def reassess_minutes(self, doc: Dict[str, Any]) -> float:
        return self._safe_call(doc.get("reassess_draw"), 12.0)
