# i4NS Environmental Forecast Monitor

Replay hourly observations from NOAA National Data Buoy Center station 44009 off Delaware Bay. The dashboard shows how a threshold-based alert can trigger short-term updates to a simulated daily environmental forecast. It is a local historical research prototype for the Innovation for National Security project.

## Install and run

Install Python 3.13 and Node.js 22.18+ (22.x) or Node.js 24+. From the repository root:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --prefix web
./run.sh
```

Open <http://localhost:8000>. The launcher builds the React dashboard with Vite and serves it and the API from FastAPI on the same origin. The checked-in NOAA archives and trained PyTorch model are sufficient for the demo. No hosted services or CDN assets are required to replay it.

If the model artifact is missing, restore `artifacts/radar_mlp.pt` from the checkout or run `.venv/bin/python scripts/train.py`. The training script downloads the NOAA archives if they are absent and writes the model artifact.

## Use the dashboard

- **Historical date** loads a day and starts playback at 08:00 Eastern. Use the adjacent buttons to move one day at a time. **Demo day** returns to December 4, 2024. July 15, 2024 is an example without a confirmed alert.
- **Simulation timeline** offers play, pause, single-hour steps in either direction, reset, a time slider, and three speeds. Playback reveals observations, alerts, and model issuances through the selected hour. Dragging the slider backward also hides that later information.
- **Environmental measurements** shows each variable’s observation, baseline, difference, and rule status. When a previous model issuance predicted the selected hour, the card includes that prediction and its issue time. Select a card to change the chart, then hover over or focus the chart to explore hourly values.
- **Forecast deviation detected** identifies the first confirmed alert and its triggering variables. **Jump to alert** becomes available when the alert is reached, and activity log entries jump to their event hour.
- **Neural forecast updates** shows all six targets from the latest issuance available at the selected hour. The chart and table carry the model horizon past 20:00 when applicable. Baseline comparisons are available for targets through 20:00.

## Science and limitations

The stand-in forecast is anchored to the 08:00 local buoy observation. It follows the typical hourly pattern for the month, computed from 2023 observations. Its displayed forecast window is 08:00–20:00 in America/New_York. It simulates a daily forecast for research purposes. Live monitoring and operational Navy forecasting are outside the prototype’s scope.

The prototype confirms a deviation when the same variable meets its deviation criteria for two consecutive hours, with the second hour as the alert time. Wind uses a difference of at least 10 knots (about 11.5 mph) and requires either the observed or forecast speed to reach 12 knots (about 13.8 mph). The chart shows the wind difference band, and the alert also applies the minimum-speed condition. The wind criteria and persistence approach are based on [NWS Instruction 10-813](https://www.weather.gov/media/directives/010_pdfs/pd01008013curr.pdf). The other thresholds are empirical, at ±3 °C for air temperature, ±15 percentage points for relative humidity, ±1.5 °C for sea temperature, and ±5 hPa for atmospheric pressure. Relative humidity is derived from air temperature and dew point.

After confirmation, the PyTorch model can issue a new forecast each hour through 19:00 when the required six-hour observation window is complete. It predicts wind speed, air temperature, relative humidity, sea temperature, and pressure one to six hours ahead. Training uses 2023 data and evaluation uses 2024 data. Radar detection range, propagation loss, and coverage are outside the model’s scope. The long-term research goal is to support more responsive radar-performance estimation as atmospheric conditions change.

## Development and verification

For frontend development, run the API and Vite in separate terminals. Vite proxies `/api` to port 8000, so the frontend can use the same relative URLs in both modes.

```sh
.venv/bin/python -m uvicorn api:app --port 8000
npm run dev --prefix web
```

Open the URL printed by Vite. The API endpoint is `GET /api/day?date=2024-12-04`.

```sh
.venv/bin/python -m pytest -q
npm run typecheck --prefix web
npm test --prefix web
npm run build --prefix web
```

The original Python workflows remain available:

```sh
.venv/bin/python scripts/train.py
.venv/bin/python scripts/evaluate.py
.venv/bin/python scripts/run_demo.py
.venv/bin/python scripts/run_demo.py --date 2024-07-15
```
