# edems/doctor.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
import simpy


@dataclass
class _DoctorSpec:
    name: str
    area: str
    assess_time_draw: Callable[[], float]
    max_active_panel: int


class DoctorManagerMixin:
    """
    Very simple doctor manager:
      - Each doctor has a panel capacity (max_active_panel).
      - A patient 'holds' one panel slot from the start of assessment
        until discharge (180 min).
      - We ignore shift windows & signups for now (kept for later).
    """

    def _init_doctors(self):
        """Build per-area doctor lists & token containers."""
        self._docs_by_area: Dict[str, List[_DoctorSpec]] = {}
        self._doc_tokens: Dict[str, simpy.Container] = {}
        self._doc_specs: Dict[str, _DoctorSpec] = {}  # name -> spec

        # group by area
        for d in getattr(self.cfg, "doctors", []) or []:
            spec = _DoctorSpec(
                name=d.name,
                area=d.area,
                assess_time_draw=d.assess_time_draw,
                max_active_panel=int(d.max_active_panel),
            )
            self._docs_by_area.setdefault(d.area, []).append(spec)
            self._doc_specs[d.name] = spec

        # sanity: at least one doctor per referenced area (FAST included if enabled)
        areas_needing_docs = set(self._cap.keys())
        if self._ft_enabled and self._ft_cap > 0:
            areas_needing_docs.add(self._ft_name)

        for area in sorted(areas_needing_docs):
            if area not in self._docs_by_area or not self._docs_by_area[area]:
                raise ValueError(
                    f"No doctors configured for area '{area}'. "
                    f"Add a DoctorConfig(area='{area}', ...)."
                )

        # one shared token container per area that reflects TOTAL panel capacity in that area
        for area, specs in self._docs_by_area.items():
            total_panel = sum(s.max_active_panel for s in specs)
            # Container level == available panel slots in the area
            self._doc_tokens[area] = simpy.Container(self.env, init=total_panel, capacity=total_panel)

    def _acquire_doctor_panel(self, area: str):
        """Yield until an area has at least one free panel slot, then take it."""
        tokens = self._doc_tokens[area]
        # Wait until a slot is available; this is FIFO across all waiters.
        return tokens.get(1)

    def _release_doctor_panel(self, area: str):
        """Return a previously acquired panel slot to the area."""
        tokens = self._doc_tokens[area]
        return tokens.put(1)

    def _draw_assess_minutes(self, area: str) -> float:
        """
        For simplicity, pick the FIRST doctor's assess draw in the area.
        (We can extend to pick an actual doctor by round-robin later.)
        """
        spec = self._docs_by_area[area][0]
        try:
            return float(spec.assess_time_draw())
        except Exception:
            return 15.0  # safe fallback

