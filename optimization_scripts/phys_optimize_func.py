# Re-run after state reset
import numpy as np
import pandas as pd
import math
from typing import List, Tuple, Dict, Any, Optional

Z90 = 1.2815515655446004

def _lognorm_params_from_median_p90(median: float, p90: float) -> Tuple[float, float]:
    mu = math.log(float(median))
    sigma = (math.log(float(p90)) - mu) / Z90
    return mu, sigma

def _build_doc_capacity(shift_starts: List[int], profile: np.ndarray, horizon: int = 24) -> np.ndarray:
    cap = np.zeros(horizon, dtype=int)
    for s in shift_starts:
        s = int(s) % horizon
        for i, v in enumerate(profile):
            cap[(s + i) % horizon] += int(v)
    return cap

def _active_doctors_by_hour(shift_starts: List[int], horizon: int = 24) -> np.ndarray:
    active = np.zeros(horizon, dtype=int)
    for s in shift_starts:
        s = int(s) % horizon
        for i in range(8):
            active[(s + i) % horizon] += 1
    return active

def _count_starts_in_window(shift_starts: List[int], a: int, b: int, horizon: int = 24) -> int:
    a %= horizon; b %= horizon
    if a <= b:
        return sum(1 for s in shift_starts if a <= (s % horizon) <= b)
    else:
        return sum(1 for s in shift_starts if (s % horizon) >= a or (s % horizon) <= b)

def _violates_constraints(
    total_starts: List[int],
    added_starts: List[int],
    candidate_hour: int,
    forbid_same_hour: bool,
    hourly_start_limits: Optional[Dict[int, int]],
    start_window_limits: Optional[List[Tuple[int, int, int]]],
    active_doctor_limits: Optional[Dict[int, int]],
    constraints_apply_to_added_only: bool,
    horizon: int = 24
) -> bool:
    prospective_added = list(added_starts) + [candidate_hour]
    schedule_for_constraints = prospective_added if constraints_apply_to_added_only else list(total_starts) + [candidate_hour]

    if forbid_same_hour:
        counts = {}
        for s in schedule_for_constraints:
            counts[s % horizon] = counts.get(s % horizon, 0) + 1
        if any(c > 1 for c in counts.values()):
            return True

    if hourly_start_limits:
        counts = {}
        for s in schedule_for_constraints:
            h = s % horizon
            counts[h] = counts.get(h, 0) + 1
        for h, maxc in hourly_start_limits.items():
            if counts.get(h % horizon, 0) > int(maxc):
                return True

    if start_window_limits:
        for (a, b, maxc) in start_window_limits:
            if _count_starts_in_window(schedule_for_constraints, int(a), int(b), horizon) > int(maxc):
                return True

    if active_doctor_limits:
        active = _active_doctors_by_hour(schedule_for_constraints, horizon)
        for h, maxc in active_doctor_limits.items():
            if active[h % horizon] > int(maxc):
                return True

    return False

def _simulate_days(
    arrival_lambda_by_hour: np.ndarray,
    capacity_spaces: int,
    doctor_profile: np.ndarray,
    shift_starts: List[int],
    p_long: float,
    short_mu: float, short_sigma: float,
    long_mu: float, long_sigma: float,
    days: int = 60,
    warmup_days: int = 30,
    seed: int = 12345,
    track_hourly: bool = False,
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    doc_cap_daily = _build_doc_capacity(shift_starts, doctor_profile, 24)
    occ_remaining: List[int] = []
    queue = 0

    used_space_hours_post = 0
    capacity_hours_post = 0

    hourly_starts = np.zeros(24, dtype=float)
    post_days = 0

    for day in range(days):
        treated_day = 0
        for h in range(24):
            if occ_remaining:
                occ_remaining = [t-1 for t in occ_remaining if (t-1) > 0]
            arrivals = int(rng.poisson(arrival_lambda_by_hour[h]))
            queue += arrivals
            free_spaces = capacity_spaces - len(occ_remaining)
            starts_possible = min(doc_cap_daily[h], free_spaces, queue)
            if starts_possible > 0:
                is_long = rng.random(starts_possible) < p_long
                k_long = int(is_long.sum())
                k_short = starts_possible - k_long
                if k_short > 0:
                    s = rng.lognormal(mean=short_mu, sigma=short_sigma, size=k_short)
                    occ_remaining.extend(np.maximum(1, np.ceil(s)).astype(int).tolist())
                if k_long > 0:
                    l = rng.lognormal(mean=long_mu, sigma=long_sigma, size=k_long)
                    occ_remaining.extend(np.maximum(1, np.ceil(l)).astype(int).tolist())
                queue -= starts_possible
                treated_day += starts_possible
                if track_hourly and day >= warmup_days:
                    hourly_starts[h] += starts_possible
            if day >= warmup_days:
                used_space_hours_post += len(occ_remaining)
                capacity_hours_post += capacity_spaces
        if day >= warmup_days:
            post_days += 1

    out = {
        "avg_utilization_post_warmup": (used_space_hours_post / capacity_hours_post) if capacity_hours_post else float("nan"),
    }
    if track_hourly and post_days > 0:
        out["avg_starts_per_hour_per_day"] = (hourly_starts / post_days)
    return out

def _evaluate_schedule(
    arrival_lambda_by_hour: np.ndarray,
    capacity_spaces: int,
    doctor_profile: np.ndarray,
    shift_starts: List[int],
    p_long: float,
    short_mu: float, short_sigma: float,
    long_mu: float, long_sigma: float,
    days: int, warmup_days: int, runs: int, seed_base: int
) -> Dict[str, float]:
    treated_means = []
    ci_terms = []
    utils = []
    for i in range(runs):
        seed = seed_base + i
        rng = np.random.default_rng(seed)
        doc_cap_daily = _build_doc_capacity(shift_starts, doctor_profile, 24)
        occ_remaining: List[int] = []
        queue = 0
        used_space_hours_post = 0
        capacity_hours_post = 0
        per_day_treated = []
        for day in range(days):
            treated_day = 0
            for h in range(24):
                if occ_remaining:
                    occ_remaining = [t-1 for t in occ_remaining if (t-1) > 0]
                arrivals = int(rng.poisson(arrival_lambda_by_hour[h]))
                queue += arrivals
                free_spaces = capacity_spaces - len(occ_remaining)
                starts_possible = min(doc_cap_daily[h], free_spaces, queue)
                if starts_possible > 0:
                    is_long = rng.random(starts_possible) < p_long
                    k_long = int(is_long.sum())
                    k_short = starts_possible - k_long
                    if k_short > 0:
                        s = rng.lognormal(mean=short_mu, sigma=short_sigma, size=k_short)
                        occ_remaining.extend(np.maximum(1, np.ceil(s)).astype(int).tolist())
                    if k_long > 0:
                        l = rng.lognormal(mean=long_mu, sigma=long_sigma, size=k_long)
                        occ_remaining.extend(np.maximum(1, np.ceil(l)).astype(int).tolist())
                    queue -= starts_possible
                    treated_day += starts_possible
                if day >= warmup_days:
                    used_space_hours_post += len(occ_remaining)
                    capacity_hours_post += capacity_spaces
            per_day_treated.append(treated_day)
        eff = per_day_treated[warmup_days:]
        if len(eff) == 0:
            treated_means.append(0.0)
            ci_terms.append(0.0)
            utils.append(float("nan"))
        else:
            arr = np.array(eff, dtype=float)
            treated_means.append(arr.mean())
            sd = arr.std(ddof=1) if len(arr) > 1 else 0.0
            ci_hw = 1.96 * sd / math.sqrt(max(1, len(arr)))
            ci_terms.append(ci_hw)
            utils.append((used_space_hours_post / capacity_hours_post) if capacity_hours_post else float("nan"))
    return {
        "treated_mean_after_warmup": float(np.mean(treated_means)),
        "treated_ci95_halfwidth":  float(np.mean(ci_terms)),
        "avg_utilization_post_warmup": float(np.nanmean(utils)),
    }

def optimize_and_profile(
    doctors_to_add: int,
    current_schedule: List[int],
    arrival_trends: List[float],
    prob_long_stay: float,
    median_long: float, p90_long: float,
    median_short: float, p90_short: float,
    treatment_spaces: int,
    doctor_profile: List[int] = None,
    days: int = 60, warmup_days: int = 30,
    runs_per_candidate: int = 8, seed: int = 12345,
    # Constraints
    forbid_same_hour: bool = False,
    hourly_start_limits: Optional[Dict[int,int]] = None,
    start_window_limits: Optional[List[Tuple[int,int,int]]] = None,
    active_doctor_limits: Optional[Dict[int,int]] = None,
    constraints_apply_to_added_only: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[int]]:
    if len(arrival_trends) != 24:
        raise ValueError("arrival_trends must be a 24-length list of hourly means")
    arrival = np.array(arrival_trends, dtype=float)
    cap = int(treatment_spaces)
    prof = np.array(doctor_profile if doctor_profile is not None else [6,4,3,2,1,1,0,0], dtype=int)
    p_long = float(prob_long_stay)

    short_mu, short_sigma = _lognorm_params_from_median_p90(median_short, p90_short)
    long_mu, long_sigma   = _lognorm_params_from_median_p90(median_long, p90_long)

    base = [int(x) % 24 for x in current_schedule]
    added: List[int] = []

    summary_rows = []
    for step in range(1, doctors_to_add + 1):
        best_h = None
        best_metrics = None
        for h in range(24):
            if _violates_constraints(
                total_starts=base + added,
                added_starts=added,
                candidate_hour=h,
                forbid_same_hour=forbid_same_hour,
                hourly_start_limits=hourly_start_limits,
                start_window_limits=start_window_limits,
                active_doctor_limits=active_doctor_limits,
                constraints_apply_to_added_only=constraints_apply_to_added_only,
            ):
                continue
            candidate = base + added + [h]
            metrics = _evaluate_schedule(
                arrival, cap, prof, candidate,
                p_long, short_mu, short_sigma, long_mu, long_sigma,
                days, warmup_days, runs_per_candidate, seed + 1000*step + 10*h
            )
            if (best_h is None) or (metrics["treated_mean_after_warmup"] > best_metrics["treated_mean_after_warmup"]) or \
               (metrics["treated_mean_after_warmup"] == best_metrics["treated_mean_after_warmup"] and h < best_h):
                best_h, best_metrics = h, metrics
        if best_h is None:
            summary_rows.append({
                "step": step,
                "chosen_hours": tuple(sorted(base + added)),
                "treated_mean_after_warmup": float("nan"),
                "treated_ci95_halfwidth": float("nan"),
                "avg_utilization_post_warmup": float("nan"),
                "note": "No feasible hour to add without violating constraints"
            })
            break
        added.append(best_h)
        summary_rows.append({
            "step": step,
            "chosen_hours": tuple(sorted(base + added)),
            **best_metrics
        })
    summary_df = pd.DataFrame(summary_rows)

    # Hourly profile for final schedule
    final_schedule = base + added
    hour_vecs = []
    runs_for_final = max(8, runs_per_candidate)
    for i in range(runs_for_final):
        sim = _simulate_days(
            arrival, cap, prof, final_schedule,
            p_long, short_mu, short_sigma, long_mu, long_sigma,
            days=days, warmup_days=warmup_days, seed=seed + 7777 + i, track_hourly=True
        )
        hour_vecs.append(sim["avg_starts_per_hour_per_day"])
    hourly_avg = np.mean(np.vstack(hour_vecs), axis=0)
    hourly_df = pd.DataFrame({"hour": list(range(24)), "avg_starts_per_hour_per_day": hourly_avg})

    return summary_df, hourly_df, final_schedule

cap_by_hour = {h: 1 for h in range(0, 6)}     # 0–5  -> max 1
cap_by_hour |= {h: 5 for h in range(6, 24)}   # 6–23 -> max 4

# ---------------- Demo call with your defaults ----------------
summary_df, hourly_counter, final_schedule = optimize_and_profile(
    doctors_to_add=8,
    current_schedule=[],
    arrival_trends=[5, 5, 5, 5, 5, 3, 3, 3, 4, 5, 7, 8, 7, 7, 7, 6, 7, 6, 7, 6, 6, 6, 6, 6],
    prob_long_stay=0.04,
    median_long=12.57, p90_long=25.83,
    median_short=7.68, p90_short=14.15,
    treatment_spaces=100,
    doctor_profile=[7,6,6,4,3,2,1,0],
    forbid_same_hour=True,
    active_doctor_limits=cap_by_hour,
    constraints_apply_to_added_only=True,
    runs_per_candidate=4, days=50, warmup_days=20, seed=2468
)

summary_df.to_csv('best_schedule.csv')


# Show outputs





