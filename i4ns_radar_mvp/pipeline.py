"""Run the full pipeline for one day: forecast -> bounds -> flag -> NN update."""
from functools import lru_cache

import numpy as np
import pandas as pd

from .bounds import make_bounds, find_flag, out_of_bounds
from .data import VARS, load_years
from .forecast import forecast_day, climatology, LAST_HOUR, ISSUE_HOUR
from .model import Predictor, LOOK, AHEAD

TRAIN_YEAR, TEST_YEAR = 2023, 2024


@lru_cache(maxsize=1)
def resources():
    hourly = load_years([TRAIN_YEAR, TEST_YEAR])
    clim = climatology(hourly[hourly.index.year == TRAIN_YEAR])  # 2023 only
    return hourly, clim


def window(hourly, t):
    """Observations for hours t-5..t, or None if any is missing/outside the data."""
    idx = pd.date_range(end=t, periods=LOOK, freq="h")
    if idx[0] < hourly.index[0] or t > hourly.index[-1]:
        return None
    w = hourly.loc[idx].values
    return None if np.isnan(w).any() else w


def run_day(date, predictor, hourly=None, clim=None):
    """Returns dict with 'table' (hourly DataFrame 08:00-20:00), 'flag', 'paths'
    or None if the day can't be forecast (missing 08:00 obs)."""
    if hourly is None:
        hourly, clim = resources()
    fc_full = forecast_day(hourly, clim, date)
    if fc_full is None:
        return None
    times = fc_full.index
    day = times[times.hour.isin(range(ISSUE_HOUR, LAST_HOUR + 1)) & (times.date == times[0].date())]
    fc = fc_full.loc[day]
    actual = hourly.reindex(day)
    lo, hi = make_bounds(fc)
    flag = find_flag(actual, lo, hi)

    updated = pd.DataFrame(np.nan, index=day, columns=VARS)
    paths = {}  # origin time -> (6,5) predicted path
    if flag is not None and predictor is not None:
        for t in day[day >= flag["time"]]:
            if t.hour >= LAST_HOUR:
                break
            w = window(hourly, t)
            if w is None:
                continue
            fc_next = fc_full.loc[t + pd.Timedelta(hours=1): t + pd.Timedelta(hours=AHEAD)].values
            if fc_next.shape[0] < AHEAD or np.isnan(fc_next).any():
                continue
            p = predictor.predict(w, fc_next, t)
            paths[t] = p
            for k in range(AHEAD):          # later origins overwrite -> most recent prediction wins
                h = t + pd.Timedelta(hours=k + 1)
                if h in updated.index:
                    updated.loc[h] = p[k]
    table = {"forecast": fc, "lo": lo, "hi": hi, "actual": actual,
             "in_bounds": ~out_of_bounds(actual, lo, hi), "nn_updated": updated}
    return {"date": pd.Timestamp(date).date(), "tables": table, "flag": flag, "paths": paths,
            "hourly": hourly}


def after_flag_errors(res):
    """Absolute errors for hours after the flag hour (until 20:00), per variable.
    Returns dict of DataFrames: forecast / nn / persist (index = hours), or None.
    persistence = last available observation before that hour, held."""
    flag = res["flag"]
    if flag is None:
        return None
    T = res["tables"]
    hours = T["actual"].index[T["actual"].index > flag["time"]]
    if len(hours) == 0:
        return None
    hourly = res["hourly"]
    persist = pd.DataFrame(np.nan, index=hours, columns=VARS)
    for h in hours:
        persist.loc[h] = hourly.loc[:h - pd.Timedelta(hours=1)].ffill(limit=2).iloc[-1].values
    a = T["actual"].loc[hours]
    return {"forecast": (T["forecast"].loc[hours] - a).abs(),
            "nn": (T["nn_updated"].loc[hours] - a).abs(),
            "persist": (persist - a).abs()}


def lead_errors(res):
    """Rows (lead, var, fc_err, nn_err, persist_err) for every origin hour >= flag hour
    and lead 1..6 with target <= 20:00 (NN path from that origin vs actual)."""
    rows = []
    flag, T = res["flag"], res["tables"]
    if flag is None:
        return rows
    for t, p in res["paths"].items():
        for k in range(AHEAD):
            h = t + pd.Timedelta(hours=k + 1)
            if h not in T["actual"].index:
                continue
            a = T["actual"].loc[h]
            cur = res["hourly"].loc[t]
            for j, v in enumerate(VARS):
                if np.isnan(a[v]) or np.isnan(cur[v]):
                    continue
                rows.append((k + 1, v, abs(T["forecast"].loc[h, v] - a[v]),
                             abs(p[k, j] - a[v]), abs(cur[v] - a[v])))
    return rows
