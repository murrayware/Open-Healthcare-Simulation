from typing import Dict, Optional

def snct_required_staff(
    patient_counts: Dict[str, float],
    multipliers_hrs_per_patient_24h: Dict[str, float],
    specials_hours_24h: float = 0.0,
    non_patient_overhead_hours_24h: float = 0.0,
    uplift_rate: float = 0.22,  # e.g., 22% uplift
    contracted_hours_per_WTE_year: float = 37.5 * 52.18,  # NHS-style default ≈ 1956.75
    # Optional shift breakdown
    shift_split: Optional[Dict[str, float]] = None,  # e.g., {"day":0.4,"evening":0.4,"night":0.2}
    rn_skill_mix: float = 0.6,       # proportion of RN hours (rest assumed HCA or other)
    shift_length_hours: float = 12.0 # hours per shift to get headcount
) -> Dict:
    """
    Calculate required nursing staffing using SNCT-style logic.

    Parameters
    ----------
    patient_counts : dict
        Mapping of category -> patient count in the last 24h (e.g. {"Cat1": 10, "Cat2": 8}).
    multipliers_hrs_per_patient_24h : dict
        Mapping of category -> nursing hours per patient per 24h (must match categories in patient_counts).
    specials_hours_24h : float
        Extra 1:1 or specialing hours over the 24h period (total).
    non_patient_overhead_hours_24h : float
        Ward-level overhead / non-patient-facing hours to include over 24h.
    uplift_rate : float
        Proportion to add for leave/training/etc. (e.g., 0.22 for 22%).
    contracted_hours_per_WTE_year : float
        Annual paid hours per WTE, used to convert hours -> WTE.
    shift_split : dict or None
        Optional mapping of shift name -> proportion of the 24h hours (must sum to 1.0 if given).
        If None, uses {"day":0.4, "evening":0.4, "night":0.2}.
    rn_skill_mix : float
        Proportion of RN hours in each shift (0..1). Remainder is non-RN (e.g., HCA).
    shift_length_hours : float
        Shift length used to convert hours -> headcount-on-duty for that shift.

    Returns
    -------
    dict with keys:
      - raw_daily_hours
      - required_daily_hours
      - required_annual_hours
      - required_WTE
      - shifts (if shift_split provided or defaulted):
          { shift: {
              "total_hours", "rn_hours", "non_rn_hours",
              "headcount_total", "headcount_rn", "headcount_non_rn"
            }, ... }
    """
    # --- Validate categories
    missing = [k for k in patient_counts.keys() if k not in multipliers_hrs_per_patient_24h]
    if missing:
        raise ValueError(f"Missing multipliers for categories: {missing}")

    # --- Core math
    raw_category_hours = sum(
        float(patient_counts.get(cat, 0.0)) * float(multipliers_hrs_per_patient_24h[cat])
        for cat in patient_counts
    )
    raw_daily_hours = raw_category_hours + float(specials_hours_24h) + float(non_patient_overhead_hours_24h)
    required_daily_hours = raw_daily_hours * (1.0 + float(uplift_rate))
    required_annual_hours = required_daily_hours * 365.0
    required_WTE = required_annual_hours / float(contracted_hours_per_WTE_year)

    result = {
        "raw_daily_hours": raw_daily_hours,
        "required_daily_hours": required_daily_hours,
        "required_annual_hours": required_annual_hours,
        "required_WTE": required_WTE
    }

    # --- Shifts & skill mix
    if shift_split is None:
        shift_split = {"day": 0.4, "evening": 0.4, "night": 0.2}

    total_prop = sum(shift_split.values())
    if abs(total_prop - 1.0) > 1e-6:
        raise ValueError(f"shift_split proportions must sum to 1.0 (got {total_prop:.6f}).")

    if not (0.0 <= rn_skill_mix <= 1.0):
        raise ValueError("rn_skill_mix must be between 0 and 1.")

    shifts_out = {}
    for shift_name, prop in shift_split.items():
        h_shift = required_daily_hours * float(prop)
        rn_h = h_shift * float(rn_skill_mix)
        non_rn_h = h_shift - rn_h
        headcount_total = h_shift / float(shift_length_hours)
        headcount_rn = rn_h / float(shift_length_hours)
        headcount_non_rn = non_rn_h / float(shift_length_hours)
        shifts_out[shift_name] = {
            "total_hours": h_shift,
            "rn_hours": rn_h,
            "non_rn_hours": non_rn_h,
            "headcount_total": headcount_total,
            "headcount_rn": headcount_rn,
            "headcount_non_rn": headcount_non_rn
        }

    result["shifts"] = shifts_out
    return result


patient_counts = {"Cat1": 10, "Cat2": 8, "Cat3": 6, "Cat4": 4}
multipliers = {"Cat1": 3.0, "Cat2": 4.0, "Cat3": 5.5, "Cat4": 6.9}  # hrs per pt per 24h (illustrative)

out = snct_required_staff(
    patient_counts=patient_counts,
    multipliers_hrs_per_patient_24h=multipliers,
    specials_hours_24h=12,
    non_patient_overhead_hours_24h=4,
    uplift_rate=0.22,
    shift_split={"day":0.4, "evening":0.4, "night":0.2},
    rn_skill_mix=0.6,
    shift_length_hours=12
)

print(out["required_daily_hours"], "hours / 24h")
print(out["required_WTE"], "WTE")
print(out["shifts"]["day"])

