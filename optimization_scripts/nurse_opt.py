# pip install pulp
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, PULP_CBC_CMD

def build_biweekly_34_pattern():
    """
    14-day cyclic ON/OFF vector for 12h nurses doing:
      Week A: 3 ON, 4 OFF
      Week B: 4 ON, 3 OFF
    As consecutive-day blocks: [1,1,1,0,0,0,0, 1,1,1,1, 0,0,0]
    """
    return [1,1,1, 0,0,0,0, 1,1,1,1, 0,0,0]  # length 14, sum = 7

def optimize_min_nurses_biweekly_12h(
    num_beds=30,
    shift_labels=("Day","Night"),
    pattern=None,
    solver=None
):
    """
    Minimize total nurses for a 14-day cyclic schedule:
      - 1 nurse per bed per shift
      - Fixed 14-day ON/OFF pattern (e.g., 3-4 biweekly: 7 ON days)
      - Aggregated integer decision variables: starts by (shift, 14-day offset)

    Returns a dict with status, headcount, and starts per 14-day offset.
    """
    if pattern is None:
        pattern = build_biweekly_34_pattern()
    H = len(pattern)  # should be 14
    S = list(shift_labels)
    K = list(range(H))  # start offsets 0..H-1

    # Decision vars: a[s,k] = number of nurses whose cycle starts at offset k on shift s
    a = {(s,k): LpVariable(f"a_{s}_{k}", lowBound=0, cat="Integer") for s in S for k in K}

    m = LpProblem("MinNurses_12h_Biweekly34", LpMinimize)

    # Objective: minimize total nurses
    m += lpSum(a[s,k] for s in S for k in K)

    # Coverage: for each day t in the 14-day cycle and shift s, need num_beds nurses ON
    # If a block starts at k, it contributes on day t iff pattern[(t - k) % H] == 1
    for t in range(H):
        for s in S:
            m += lpSum(a[s,k] * pattern[(t - k) % H] for k in K) >= num_beds, f"cover_{s}_t{t}"

    # Solve
    status = m.solve(PULP_CBC_CMD(msg=False) if solver is None else solver)

    result = {
        "status": LpStatus[status],
        "total_nurses": int(round(sum(v.value() for v in a.values()))),
        "by_shift_offset": {
            s: {k: int(round(a[s,k].value())) for k in K} for s in S
        },
        "pattern": pattern,
        "pattern_len": H,
        "shift_labels": S,
        "num_beds": num_beds
    }
    return result

def pretty_print_result(title, res):
    print(f"\n=== {title} ===")
    print("Status:", res["status"])
    print("Beds per shift:", res["num_beds"])
    print("Shift labels:", res["shift_labels"])
    print(f"Pattern length: {res['pattern_len']}  ON-days in cycle: {sum(res['pattern'])}")
    print("Pattern (1=ON,0=OFF):", res["pattern"])
    print("Minimum nurses:", res["total_nurses"])
    print("Starts per 14-day offset (0..13) by shift:")
    for s in res["shift_labels"]:
        starts = res["by_shift_offset"][s]
        line = ", ".join(f"{k}:{starts[k]}" for k in range(res["pattern_len"]))
        print(f"  {s}: {line}")

if __name__ == "__main__":
    # 12-hour, Day/Night, biweekly 3-4 pattern
    res = optimize_min_nurses_biweekly_12h(
        num_beds=30,
        shift_labels=("Day","Night"),
        pattern=build_biweekly_34_pattern()
    )
    pretty_print_result("12-hour biweekly 3-4 (min staff)", res)

