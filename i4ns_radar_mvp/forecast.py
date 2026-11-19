"""Stand-in for the Navy forecast.

Plain English: every day at 08:00 local we look at what the buoy actually
measured, then say "the rest of the day will follow the usual daily pattern for
this month, shifted so it starts from what we see right now".

    forecast(hour h) = observation at 08:00 + (typical value at h - typical value at 08:00)

"Typical" = the average for that hour of the day over that calendar month in
2023 (the month's typical daily pattern; computed from 2023 only).

Example: 8am wind is 10 mph and August wind typically rises 3 mph by 2pm,
so the forecast for 2pm is 13 mph.

The forecast is meant for 08:00-20:00; we compute it a few hours further
(until 02:00 next day) only because the neural net looks 6 hours ahead.
"""
import numpy as np
import pandas as pd

from .data import VARS

ISSUE_HOUR = 8
LAST_HOUR = 20       # last hour of the official forecast window
N_HOURS = 19         # 08:00 .. 02:00 next day (extended)


def climatology(hourly_train):
    """Mean of each variable by (month, hour-of-day), from the training year only."""
    g = hourly_train.groupby([hourly_train.index.month, hourly_train.index.hour]).mean()
    g.index.names = ["month", "hour"]
    return g


def day_times(date):
    start = pd.Timestamp(date).normalize() + pd.Timedelta(hours=ISSUE_HOUR)
    return pd.date_range(start, periods=N_HOURS, freq="h")


def forecast_day(hourly, clim, date):
    """Return DataFrame (index = local times 08:00..02:00+1d, columns = VARS) or None
    if the 08:00 observation is missing for wind/temp/rh."""
    times = day_times(date)
    if times[0] not in hourly.index:
        return None
    obs0 = hourly.loc[times[0]]
    if obs0[["wind", "temp", "rh"]].isna().any():
        return None
    typ = np.array([clim.loc[(t.month, t.hour)].values for t in times])
    fc = obs0.values[None, :] + (typ - typ[0])
    fc = pd.DataFrame(fc, index=times, columns=VARS)
    fc["rh"] = fc["rh"].clip(0, 100)
    fc["wind"] = fc["wind"].clip(lower=0)
    return fc
