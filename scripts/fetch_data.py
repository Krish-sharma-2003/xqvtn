import json, time, datetime as dt, urllib.parse, urllib.request, urllib.error, pathlib

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT = pathlib.Path("data"); OUT.mkdir(exist_ok=True)

def get(path, **params):
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"  retry {attempt + 1} after error: {e}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed: {url}")

def days(start, end):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)

# Actuals: 31 Dec 2025 se 2 Feb 2026
actuals = []
for d in days(dt.date(2025, 12, 31), dt.date(2026, 2, 2)):
    print("actuals", d)
    actuals += get("FUELHH/stream", settlementDateFrom=d, settlementDateTo=d, fuelType="WIND")
    time.sleep(0.3)

# Forecasts: January me publish hue sab
forecasts = {}
for d in days(dt.date(2026, 1, 1), dt.date(2026, 1, 31)):
    print("forecasts", d)
    rows = get("WINDFOR/stream",
               publishDateTimeFrom=f"{d}T00:00:00Z",
               publishDateTimeTo=f"{d}T23:59:59Z")
    for r in rows:
        forecasts[(r["publishTime"], r["startTime"])] = r
    time.sleep(0.3)

actuals = {r["startTime"]: r for r in actuals}.values()
json.dump(sorted(actuals, key=lambda r: r["startTime"]), open(OUT / "actuals.json", "w"))
json.dump(sorted(forecasts.values(), key=lambda r: (r["publishTime"], r["startTime"])),
          open(OUT / "forecasts.json", "w"))
print(len(actuals), "actual rows;", len(forecasts), "forecast rows")