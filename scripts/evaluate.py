"""Honest evaluation on all of 2024. Usage: python scripts/evaluate.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from i4ns_radar_mvp.data import VARS, UNITS
from i4ns_radar_mvp.model import Predictor
from i4ns_radar_mvp.pipeline import resources, run_day, after_flag_errors, lead_errors, TEST_YEAR


def evaluate():
    hourly, clim = resources()
    pred = Predictor()
    n_days = n_flag = n_eval = 0
    errs = {"forecast": [], "nn": [], "persist": []}
    unflag_err = []
    leads, flag_vars, flag_hours = [], {}, {}
    for date in pd.date_range(f"{TEST_YEAR}-01-01", f"{TEST_YEAR}-12-31"):
        res = run_day(date, pred, hourly, clim)
        if res is None:
            continue
        n_days += 1
        if res["flag"] is None:
            T = res["tables"]
            unflag_err.append((T["forecast"] - T["actual"]).abs().iloc[1:])   # 09:00-20:00
            continue
        n_flag += 1
        for v in res["flag"]["variables"]:
            flag_vars[v] = flag_vars.get(v, 0) + 1
        hr = res["flag"]["time"].hour
        flag_hours[hr] = flag_hours.get(hr, 0) + 1
        e = after_flag_errors(res)
        if e is None:
            continue
        n_eval += 1
        for k in errs:
            errs[k].append(e[k])
        leads += lead_errors(res)
    return dict(n_days=n_days, n_flag=n_flag, n_eval=n_eval, errs=errs, leads=leads,
                flag_vars=flag_vars, flag_hours=flag_hours, unflag_err=unflag_err)


def main():
    r = evaluate()
    print(f"Days forecastable in {TEST_YEAR}: {r['n_days']}")
    print(f"Flagged days: {r['n_flag']} = {100 * r['n_flag'] / r['n_days']:.1f}%  (with >=1 hour after the flag: {r['n_eval']})")
    hrs = sorted(h for h, c in r["flag_hours"].items() for _ in range(c))
    print(f"Median flag hour: {pd.Series(hrs).median():.1f}h")
    print("Flag hour histogram:", dict(sorted(r["flag_hours"].items())))
    print("Trigger variable (days flagged by variable; a flag may list several):", r["flag_vars"])
    cat = {k: pd.concat(v) for k, v in r["errs"].items()}
    ok = cat["forecast"].notna() & cat["nn"].notna() & cat["persist"].notna()
    un = pd.concat(r["unflag_err"])
    print("\nForecast MAE: flagged days (hours after flag) vs unflagged days (09:00-20:00)")
    print(f"{'variable':<10}{'flagged':>10}{'unflagged':>11}  unit")
    for v in VARS:
        print(f"{v:<10}{cat['forecast'][v][ok[v]].mean():>10.3f}{un[v].mean():>11.3f}  {UNITS[v]}")
    print("\nMAE for hours after the flag, overall (same hours for all methods)")
    print(f"{'variable':<10}{'n':>6}{'forecast':>10}{'NN':>10}{'persist':>10}  unit")
    for v in VARS:
        m = ok[v]
        print(f"{v:<10}{int(m.sum()):>6}{cat['forecast'][v][m].mean():>10.3f}"
              f"{cat['nn'][v][m].mean():>10.3f}{cat['persist'][v][m].mean():>10.3f}  {UNITS[v]}")
    L = pd.DataFrame(r["leads"], columns=["lead", "var", "forecast", "nn", "persist"])
    print("\nMAE by lead time (NN path from each origin hour >= flag; 'persist' = origin obs held)")
    for v in VARS:
        g = L[(L["var"] == v) & L["lead"].isin([1, 3, 6])].groupby("lead")
        s = g[["forecast", "nn", "persist"]].mean().round(3).assign(n=g.size())
        print(f"\n{v} ({UNITS[v]})")
        print(s.T.to_string())
    return r


if __name__ == "__main__":
    main()
