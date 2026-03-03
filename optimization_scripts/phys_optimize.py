import numpy as np
import pandas as pd
import math

rng = np.random.default_rng(7)

# -----------------------
# Config (easy to tweak)
# -----------------------
arrival_lambda_by_hour = np.array(
    [3,3,3,3,4,5,6,7,8,9,8,7,7,7,6,6,5,5,6,5,6,5,5,4],
    dtype=float
)
capacity_spaces = 37
base_shift_starts = [0,5,8,10,13,16,19,21]

# Tuned 8-hour front-load vector: 6 first hour, 4 second hour, strictly decreasing to 0 in last hour.
# Sum = 17 (≈ 2.125 starts/hr across 8h)
doctor_profile = np.array([4,4,2,2,2,2,1,0], dtype=int)

p_long = 0.11  # probability of long LOS (6-12h), otherwise short (2-3h)

# -----------------------
# Helpers
# -----------------------
def build_doctor_capacity(shift_starts, profile, horizon_hours=24):
    cap = np.zeros(horizon_hours, dtype=int)
    for s in shift_starts:
        for i, v in enumerate(profile):
            cap[(s + i) % horizon_hours] += v
    return cap

def sample_los_hours(local_rng):
    if local_rng.random() < p_long:
        return int(local_rng.integers(18, 22))  # 6..12 inclusive
    else:
        return int(local_rng.integers(2, 4))   # 2..3 inclusive

def simulate_days(additional_shift_start=None, days=60, warmup_days=30, seed=None):
    local_rng = np.random.default_rng(seed if seed is not None else rng.integers(0, 1_000_000))
    shift_starts = list(base_shift_starts)
    if additional_shift_start is not None:
        shift_starts.append(int(additional_shift_start))
    doc_cap_daily = build_doctor_capacity(shift_starts, doctor_profile, 24)

    # State persists across days
    occ_remaining = []  # list of remaining LOS hours for all occupied spaces
    queue = 0

    # Collect stats
    day_rows = []
    total_hours = days * 24
    space_hours_capacity = capacity_spaces * total_hours
    used_space_hours = 0
    treated_total = 0

    for day in range(days):
        treated_day = 0
        queue_start_day = queue
        for h in range(24):
            # 1) Departures
            if occ_remaining:
                occ_remaining = [t-1 for t in occ_remaining if (t-1) > 0]
            # 2) Arrivals
            arrivals = int(local_rng.poisson(arrival_lambda_by_hour[h]))
            queue += arrivals
            # 3) Starts
            free_spaces = capacity_spaces - len(occ_remaining)
            starts_possible = min(doc_cap_daily[h], free_spaces, queue)
            if starts_possible > 0:
                # allocate new patients with sampled LOS
                los_samples = local_rng.integers(2, 4, size=starts_possible)  # start with short LOS
                # overwrite some with long LOS
                long_mask = local_rng.random(starts_possible) < p_long
                los_samples[long_mask] = local_rng.integers(6, 13, size=long_mask.sum())
                occ_remaining.extend(int(x) for x in los_samples)
                queue -= starts_possible
                treated_day += starts_possible
                treated_total += starts_possible
            # 4) Utilization accounting (space-hours used at end of hour)
            used_space_hours += len(occ_remaining)
        # end-of-day record
        day_rows.append({
            "day": day,
            "treated": treated_day,
            "queue_end": queue,
            "occupied_end": len(occ_remaining)
        })

    # Aggregate results
    util = used_space_hours / space_hours_capacity  # average occupancy rate over the whole horizon
    df_days = pd.DataFrame(day_rows)
    # Slice off warmup
    eff = df_days[df_days["day"] >= warmup_days].copy()
    summary = {
        "treated_mean": eff["treated"].mean(),
        "treated_std": eff["treated"].std(ddof=1),
        "treated_min": eff["treated"].min(),
        "treated_max": eff["treated"].max(),
        "treated_ci95_halfwidth": 1.96 * eff["treated"].std(ddof=1) / math.sqrt(len(eff)) if len(eff) > 1 else float("nan"),
        "avg_utilization_overall": util,
        "queue_end_mean": eff["queue_end"].mean(),
        "occupied_end_mean": eff["occupied_end"].mean(),
        "profile_sum": int(doctor_profile.sum()),
    }
    return summary, df_days, doc_cap_daily

def evaluate_all_additions(days=60, warmup_days=30, runs=20):
    # Baseline
    base_summaries = []
    for i in range(runs):
        s, d, cap = simulate_days(None, days=days, warmup_days=warmup_days, seed=10_000+i)
        base_summaries.append(s)
    baseline_mean = np.mean([x["treated_mean"] for x in base_summaries])
    baseline_ci = 1.96 * np.std([x["treated_mean"] for x in base_summaries], ddof=1) / np.sqrt(runs)

    rows = []
    for h in range(24):
        stats = []
        for i in range(runs):
            s, d, cap = simulate_days(h, days=days, warmup_days=warmup_days, seed=1_000*h + i)
            stats.append(s)
        mean_treated = float(np.mean([x["treated_mean"] for x in stats]))
        std_treated = float(np.std([x["treated_mean"] for x in stats], ddof=1))
        ci_hw = 1.96 * std_treated / math.sqrt(runs) if runs > 1 else float("nan")
        util_mean = float(np.mean([x["avg_utilization_overall"] for x in stats]))
        rows.append({
            "add_shift_start_hour": h,
            "treated_mean_after_warmup": mean_treated,
            "treated_ci95_halfwidth": ci_hw,
            "avg_utilization_overall": util_mean,
            "delta_vs_baseline": mean_treated - baseline_mean
        })
    df = pd.DataFrame(rows).sort_values(
        ["treated_mean_after_warmup","add_shift_start_hour"],
        ascending=[False, True]
    ).reset_index(drop=True)

    baseline_row = pd.DataFrame([{
        "add_shift_start_hour": None,
        "treated_mean_after_warmup": baseline_mean,
        "treated_ci95_halfwidth": baseline_ci,
        "avg_utilization_overall": float(np.mean([x["avg_utilization_overall"] for x in base_summaries])),
        "delta_vs_baseline": 0.0
    }])
    return df, baseline_row

df, baseline = evaluate_all_additions(days=90, warmup_days=45, runs=40)

# Show ranked results to user

# Save full tables
df.to_csv('results_capped.csv')
