"""Per-hour table + plot for one day. Usage: python scripts/run_demo.py [--date YYYY-MM-DD]
Without --date, picks a 2024 demo day (flag mid-morning/midday, big wind miss, NN helps)."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from i4ns_radar_mvp.data import VARS, UNITS, LABELS, ROOT
from i4ns_radar_mvp import bounds as B
from i4ns_radar_mvp.model import Predictor
from i4ns_radar_mvp.pipeline import resources, run_day, after_flag_errors, TEST_YEAR


def pick_demo_day(pred, hourly, clim):
    """Flag at 10:00-13:00 caused by wind off by >=30%, >=5 hours after flag; choose the
    day where NN wind MAE beats the original forecast the most. (Selection is
    deliberate; see evaluate.py for the all-days numbers.)"""
    best, best_gain = None, 0
    for date in pd.date_range(f"{TEST_YEAR}-01-01", f"{TEST_YEAR}-12-31"):
        res = run_day(date, pred, hourly, clim)
        if res is None or res["flag"] is None:
            continue
        f = res["flag"]
        if not (10 <= f["time"].hour <= 13) or "wind" not in f["variables"]:
            continue
        fc = res["tables"]["forecast"].loc[f["time"], "wind"]
        if abs(f["values"]["wind"] - fc) / fc < 0.30:
            continue
        e = after_flag_errors(res)
        if e is None or e["nn"]["wind"].notna().sum() < 5:
            continue
        gain = e["forecast"]["wind"].mean() - e["nn"]["wind"].mean()
        if gain > best_gain:
            best, best_gain = date, gain
    return best


def print_table(res):
    T, flag = res["tables"], res["flag"]
    print(f"\n===== {res['date']} =====")
    for v in VARS:
        print(f"\n{LABELS[v]} ({UNITS[v]})" + ("  [wind bound = forecast ± 11.5 mph; ignored unless forecast or actual >= 13.8 mph]" if v == "wind" else ""))
        print(f"{'time':>6} | {'forecast':>8} | {'bounds lo-hi':>15} | {'actual':>7} | {'in bounds?':>10} | "
              f"{'NN updated':>10} | {'fc error':>8} | {'NN error':>8}")
        for t in T["actual"].index:
            f, lo, hi, a, nn = (T[k].loc[t, v] for k in ("forecast", "lo", "hi", "actual", "nn_updated"))
            fmt = lambda x, w: f"{x:>{w}.1f}" if not np.isnan(x) else " " * (w - 1) + "-"
            inb = "n/a" if np.isnan(a) else ("yes" if T["in_bounds"].loc[t, v] else "NO")
            print(f"{t:%H:%M} | {fmt(f, 8)} | {lo:>7.1f}-{hi:<7.1f} | {fmt(a, 7)} | {inb:>10} | "
                  f"{fmt(nn, 10)} | {fmt(f - a, 8)} | {fmt(nn - a, 8) if not np.isnan(nn) else '       -'}")
    print()
    if flag is None:
        print("FLAG: none - forecast stayed valid all day.")
    else:
        vals = ", ".join(f"{v}={x:.1f} {UNITS[v]} (bounds {flag['bounds'][v][0]:.1f}-{flag['bounds'][v][1]:.1f})"
                         for v, x in flag["values"].items())
        print(f"FLAG at {flag['time']:%Y-%m-%d %H:%M}: out of bounds {B.PERSIST_HOURS} consecutive hours -> {vals}")
        if flag["time"] in res["paths"]:
            p = res["paths"][flag["time"]]
            print(f"NN path from flag hour (next {len(p)} h), wind mph:",
                  ", ".join(f"{(flag['time'] + pd.Timedelta(hours=k + 1)):%H:%M}={p[k, 0]:.1f}" for k in range(len(p))))


def plot(res, out):
    T, flag = res["tables"], res["flag"]
    fig, axes = plt.subplots(len(VARS), 1, figsize=(9, 3 * len(VARS)), sharex=True)
    for ax, v in zip(axes, VARS):
        ax.plot(T["forecast"].index, T["forecast"][v], label="Original forecast")
        ax.fill_between(T["forecast"].index, T["lo"][v], T["hi"][v], alpha=0.25, label="Bounds (wind: ±11.5 mph, light-wind rule)" if v == "wind" else "Bounds")
        ax.plot(T["actual"].index, T["actual"][v], "ko-", ms=4, label="Actual")
        if flag is not None:
            nn = T["nn_updated"][v].copy()
            nn.loc[flag["time"]] = T["actual"].loc[flag["time"], v]   # start the line at the flag observation
            ax.plot(nn.index, nn, "r^--", ms=4, label="NN updated forecast")
            ax.axvline(flag["time"], color="red", ls=":", label="Flag")
        ax.set_ylabel(f"{LABELS[v]} ({UNITS[v]})"); ax.set_title(LABELS[v]); ax.legend(fontsize=8)
    axes[-1].set_xlabel("Local time (America/New_York)")
    fig.suptitle(f"Buoy 44009 - {res['date']}")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date")
    args = ap.parse_args()
    hourly, clim = resources(); pred = Predictor()
    date = args.date
    if date is None:
        date = pick_demo_day(pred, hourly, clim)
        print(f"Auto-selected demo day: {date:%Y-%m-%d}")
    res = run_day(date, pred, hourly, clim)
    if res is None:
        sys.exit(f"{date}: no 08:00 observation, cannot issue a forecast.")
    print_table(res)
    out = ROOT / "reports" / f"{pd.Timestamp(date):%Y-%m-%d}.png"
    out.parent.mkdir(exist_ok=True); plot(res, out); print("saved", out)


if __name__ == "__main__":
    main()
