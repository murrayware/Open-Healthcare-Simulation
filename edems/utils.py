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


import numpy as np

def make_lognormal_draw(mean: float,
                        sigma: float,
                        scale: float = 1.0,
                        cap: float | None = None,
                        floor: float | None = None):
    """
    Returns a callable that draws from a lognormal distribution.

    Parameters:
        mean, sigma : parameters of the underlying normal distribution
        scale       : multiply output (e.g., 60 to convert hours→minutes)
        cap         : optional max value clamp
        floor       : optional min value clamp
    """
    def _draw():
        val = float(np.random.lognormal(mean=mean, sigma=sigma) * scale)

        if floor is not None:
            val = max(floor, val)

        if cap is not None:
            val = min(cap, val)

        return val

    return _draw



def make_gamma_draw(mean: float, cv: float = 0.8, cap: float | None = None, floor: float = 0.0):
    """
    Return a callable that draws minutes from a Gamma distribution.

    mean: desired mean (minutes)
    cv: coefficient of variation (std/mean). Higher = heavier tail.
    cap: optional hard cap (minutes)
    floor: optional minimum (minutes)
    """
    mean = float(mean)
    cv = float(cv)
    theta = (cv ** 2) * mean          # scale
    k = mean / theta                  # shape  (since mean = k*theta)
    def _draw():
        x = float(np.random.gamma(shape=k, scale=theta))
        if floor is not None:
            x = max(float(floor), x)
        if cap is not None:
            x = min(float(cap), x)
        return x
    return _draw
