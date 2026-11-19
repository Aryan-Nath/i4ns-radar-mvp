# i4NS Radar MVP (prototype)

Stand-in "Navy" forecast for NOAA buoy 44009 (Delaware Bay): issued 08:00 local for 08:00-20:00,
bounded by fixed per-variable bounds (named constants in `i4ns_radar_mvp/bounds.py`, see below). When a variable stays out of bounds for 2 consecutive hours a flag
is raised (at the 2nd hour) and a small PyTorch MLP re-predicts the next 1-6 hours from recent observations each hour.
Train = 2023, test = 2024 (climatology also from 2023 only). Variables: wind (mph), air temp (°C),
relative humidity (%, from air temp + dewpoint), sea temp (°C), pressure (hPa). Times are America/New_York.

## Setup

    python3.13 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt

(Below, `PY=./.venv/bin/python`; scripts add the project root to `sys.path` themselves.)

## Run
Run the demo: `./run.sh` then open http://localhost:8000  (web/index.html, single static page + Plotly CDN)

    $PY scripts/train.py                         # downloads 2023 (+2024) to data/raw/, trains, saves artifacts/radar_mlp.pt
    $PY scripts/evaluate.py                      # 2024 MAE tables: forecast vs NN vs persistence
    $PY scripts/run_demo.py                      # auto-picks a demo day, prints tables, saves a PNG under reports/ (created if missing)
    $PY scripts/run_demo.py --date 2024-07-15    # any day
    $PY -m pytest -q                             # tests
    $PY -m uvicorn api:app --port 8000           # GET /api/day?date=2024-12-04

## How bounds are set
Wind thresholds and the persistence rule follow the NWS forecast-amendment criteria
(NWS Instruction 10-813, 30 Oct 2024, sec C1.3.2 and 4.7): https://www.weather.gov/media/directives/010_pdfs/pd01008013curr.pdf

- Wind: out of bounds when |actual - forecast| >= 10 kt (11.5 mph) AND (forecast >= 12 kt (13.8 mph) OR actual >= 12 kt).
  Light-wind misses are ignored. Shown bounds are forecast +/- 11.5 mph, but the light-wind rule applies on top of them.
- Other variables (no verified operational threshold; empirical, tested on 2024 buoy data): air temp +/-3 degC,
  relative humidity +/-15 %, sea temp +/-1.5 degC, pressure +/-5 hPa.
- Persistence (NWSI 10-813 sec 4.7, "criteria will persist"): a flag is raised only when a variable is out of bounds
  for 2 consecutive hours; flag time = the 2nd hour (confirmation). NN updating starts from that hour.
