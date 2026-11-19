"""Load NOAA NDBC buoy 44009 (Delaware Bay) hourly data into a clean hourly table.

Variables (columns, in this fixed order):
  wind (mph), temp (degC), rh (%), sea (degC), pres (hPa)
Index is naive local wall-clock time (America/New_York).
"""
import gzip
import io
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
STATION = "44009"
VARS = ["wind", "temp", "rh", "sea", "pres"]
UNITS = {"wind": "mph", "temp": "°C", "rh": "%", "sea": "°C", "pres": "hPa"}
LABELS = {"wind": "Wind speed", "temp": "Air temperature", "rh": "Relative humidity",
          "sea": "Sea temperature", "pres": "Pressure"}
MS_TO_MPH = 2.236936
URL = "https://www.ndbc.noaa.gov/data/historical/stdmet/{s}h{y}.txt.gz"


def download(year, station=STATION):
    """Download one year of raw data into data/raw/ (skipped if already cached)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{station}h{year}.txt.gz"
    if not path.exists():
        urllib.request.urlretrieve(URL.format(s=station, y=year), path)
    return path


def rel_humidity(temp_c, dew_c):
    """Relative humidity (%) from air temp and dewpoint (Magnus formula)."""
    a, b = 17.625, 243.04
    return 100 * np.exp(a * dew_c / (b + dew_c) - a * temp_c / (b + temp_c))


def load_year(year, station=STATION):
    path = download(year, station)
    with gzip.open(path, "rt") as f:
        lines = [l for l in f if not l.startswith("#")]
    cols = "YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS TIDE".split()
    df = pd.read_csv(io.StringIO("".join(lines)), sep=r"\s+", header=None, names=cols, na_values=["MM"])
    t = pd.to_datetime(dict(year=df.YY, month=df.MM, day=df.DD, hour=df.hh, minute=df.mm))
    df.index = t
    for c, bad in [("WSPD", 99), ("PRES", 9999), ("ATMP", 999), ("WTMP", 999), ("DEWP", 999)]:
        df.loc[df[c] >= bad, c] = np.nan
    out = pd.DataFrame({
        "wind": df.WSPD * MS_TO_MPH, "temp": df.ATMP,
        "rh": rel_humidity(df.ATMP, df.DEWP).clip(upper=100),
        "sea": df.WTMP, "pres": df.PRES})
    out = out.resample("1h").mean()  # clean hourly grid (UTC)
    out.index = out.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    out = out[~out.index.duplicated()]  # drop repeated hour at the DST fall-back
    return out.asfreq("h")[VARS]


def load_years(years):
    df = pd.concat([load_year(y) for y in years])
    return df.asfreq("h")
