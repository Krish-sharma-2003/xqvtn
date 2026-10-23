#!/usr/bin/env python3
"""M0 decision probe - one-off script for milestone M0.

What: Reads data/forecasts.json and data/actuals.json, inspects publish times
and decision forecasts per Definitions in SPEC.md.
Why: Verify understanding of cutoff/selection/alignment before building modules.
"""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path


def load_data():
    data_dir = Path(__file__).parent.parent / "data"
    with open(data_dir / "forecasts.json") as f:
        forecasts = json.load(f)
    with open(data_dir / "actuals.json") as f:
        actuals = json.load(f)
    return forecasts, actuals


def parse_dt(s):
    # All timestamps are UTC in Z format
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    dt = datetime.fromisoformat(s)
    return dt


def main():
    forecasts, actuals = load_data()
    
    # 1. Print the publishTimes (UTC) of all forecast publishes on 2026-01-14.
    print("=== 1) Publish times (UTC) on 2026-01-14 ===")
    publish_times_14 = set()
    for row in forecasts:
        pt = parse_dt(row['publishTime'])
        if pt.date().isoformat() == '2026-01-14':
            publish_times_14.add(row['publishTime'])
    # Sort them
    for pt in sorted(list(publish_times_14)):
        print(pt)
    print()
    
    # Build indexes
    # forecasts by startTime hour
    # actuals by startTime (30-min)
    # 2. For target day 2026-01-15 with cutoff = 2026-01-14 09:00 Europe/London
    london = ZoneInfo("Europe/London")
    cutoff_london = datetime(2026, 1, 14, 9, 0, tzinfo=london)
    cutoff_utc = cutoff_london.astimezone(ZoneInfo("UTC"))
    print(f"=== 2) Target day 2026-01-15, cutoff = 2026-01-14 09:00 Europe/London = {cutoff_utc.isoformat()} ===")
    print(f"{'hour':<20} {'publishTime used':<30} {'horizon_h':<12} {'forecast MW':<15} {'hourly actual MW':<20}")
    
    # Get actuals indexed by startTime
    actuals_by_time = {}
    for a in actuals:
        actuals_by_time[a['startTime']] = a['generation']
    
    target_date = datetime(2026, 1, 15, tzinfo=ZoneInfo("UTC")).date()
    for hour in range(24):
        start_t = datetime(2026, 1, 15, hour, 0, tzinfo=ZoneInfo("UTC"))
        start_t_str = start_t.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Find candidates: rows with startTime = that hour, horizon >= 0, publishTime <= cutoff
        candidates = []
        for row in forecasts:
            if row['startTime'] == start_t_str:
                pt = parse_dt(row['publishTime'])
                if pt <= cutoff_utc:
                    horizon = (start_t - pt).total_seconds() / 3600.0  # hours
                    if horizon >= 0:  # horizon >= 0
                        candidates.append((row, pt, horizon))
        
        if not candidates:
            print(f"{start_t_str:<20} {'NONE':<30} {'N/A':<12} {'N/A':<15} {'N/A':<20}")
            continue
        
        # pick the one with max publishTime
        best = max(candidates, key=lambda x: x[1])
        row_best, pt_best, horizon_best = best
        
        # hourly actual = mean of actual[T] and actual[T+30min]
        t30 = start_t + timedelta(minutes=30)
        t30_str = t30.strftime('%Y-%m-%dT%H:%M:%SZ')
        actual_t = actuals_by_time.get(start_t_str)
        actual_t30 = actuals_by_time.get(t30_str)
        if actual_t is not None and actual_t30 is not None:
            hourly_actual = (actual_t + actual_t30) / 2.0
        else:
            hourly_actual = None
        
        print(f"{start_t_str:<20} {pt_best.strftime('%Y-%m-%dT%H:%M:%SZ'):<30} {horizon_best:<12.1f} {row_best['generation']:<15.1f} {hourly_actual if hourly_actual is not None else 'MISSING':<20}")
    print()
    
    # 3. For every target day from 2026-01-02 to 2026-02-01 with the same rule
    print("=== 3) Range 2026-01-02 to 2026-02-01: min/max horizon overall, missing (day,hour) pairs ===")
    all_horizons = []
    missing = []
    
    from datetime import date
    start_day = date(2026, 1, 2)
    end_day = date(2026, 2, 1)
    cur = start_day
    while cur <= end_day:
        target_day_str = cur.isoformat()
        # cutoff = previous day 09:00 Europe/London
        prev_day = cur - timedelta(days=1)
        cutoff_london_d = datetime(prev_day.year, prev_day.month, prev_day.day, 9, 0, tzinfo=london)
        cutoff_utc_d = cutoff_london_d.astimezone(ZoneInfo("UTC"))
        
        for hour in range(24):
            start_t = datetime(cur.year, cur.month, cur.day, hour, 0, tzinfo=ZoneInfo("UTC"))
            start_t_str = start_t.strftime('%Y-%m-%dT%H:%M:%SZ')
            t30_str = (start_t + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # find best forecast
            candidates = []
            for row in forecasts:
                if row['startTime'] == start_t_str:
                    pt = parse_dt(row['publishTime'])
                    if pt <= cutoff_utc_d:
                        horizon = (start_t - pt).total_seconds() / 3600.0
                        if horizon >= 0:
                            candidates.append((row, pt, horizon))
            
            if not candidates:
                missing.append((target_day_str, hour, 'no_valid_forecast'))
                continue
            
            best = max(candidates, key=lambda x: x[1])
            _, pt_best, horizon_best = best
            all_horizons.append(horizon_best)
            
            # check actual
            if actuals_by_time.get(start_t_str) is None or actuals_by_time.get(t30_str) is None:
                missing.append((target_day_str, hour, 'no_actual'))
                continue
        
        cur += timedelta(days=1)
    
    if all_horizons:
        print(f"Min horizon: {min(all_horizons):.1f}h, Max horizon: {max(all_horizons):.1f}h")
    else:
        print("No horizons found")
    print(f"Missing count: {len(missing)}")
    if missing:
        for m in missing:
            print(f"  MISSING: day={m[0]} hour={m[1]} reason={m[2]}")
    print()


if __name__ == '__main__':
    main()
