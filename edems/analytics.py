from __future__ import annotations
from typing import Tuple

try:
    import pandas as pd
except Exception:
    pd = None  # type: ignore


def summarize_patients(patients_df, events_df) -> Tuple["pd.DataFrame", "pd.DataFrame"]:
    """
    Returns (detailed, summary). For arrivals-only, we compute hourly arrival counts
    and basic acuity stats. API stays stable for future metrics.
    """
    if pd is None or not hasattr(patients_df, "__class__"):
        # Fallback: no pandas → return passthrough
        return patients_df, []

    # Detailed per-patient metrics (placeholder for future LOS, etc.)
    detailed = patients_df.copy()

    # Summary by clock-hour
    patients_df = patients_df.copy()
    patients_df["abs_hour"] = (patients_df["arrival"] // 60).astype(int)
    grp = (
        patients_df.groupby("abs_hour", as_index=False)
        .agg(n=("pid", "size"), acuity_mean=("acuity", "mean"))
    )
    grp["hod"] = grp["abs_hour"] % 24
    grp.rename(columns={"n": "arrivals"}, inplace=True)

    return detailed, grp[["abs_hour", "hod", "arrivals", "acuity_mean"]]
