from __future__ import annotations
from typing import List, Dict, Any
import random

def u(a: float, b: float) -> float:
    """Uniform draw helper used across modules."""
    return random.uniform(a, b)

try:
    import pandas as pd
except Exception:
    pd = None  # type: ignore

class EventLog:
    """Minimal event logger with DataFrame export."""
    def __init__(self) -> None:
        self._rows: List[Dict[str, Any]] = []

    def add(self, t: float, event: str, **kwargs: Any) -> None:
        row = {"t": float(t), "event": event}
        row.update(kwargs)
        self._rows.append(row)

    def to_df(self):
        if pd is None:
            # Fallback: return list for print/debug
            return list(self._rows)
        return pd.DataFrame(self._rows).sort_values(["t", "event"]).reset_index(drop=True)
