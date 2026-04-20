"""
SHINDO — Step 1: Fetch Japan earthquake data from USGS
=======================================================
Run this first. It pulls M5.0+ events for Japan (1950–2024)
from the free USGS Earthquake Hazards API and saves them to
data/earthquakes_raw.json.

Usage:
    python 01_fetch_usgs.py

Output:
    data/earthquakes_raw.json
"""

import requests
import json
import time
import os
from datetime import datetime

os.makedirs("data", exist_ok=True)

JAPAN_BBOX = {
    "minlatitude":  24,   # includes Ryukyu islands
    "maxlatitude":  46,   # includes Hokkaido
    "minlongitude": 122,
    "maxlongitude": 148,
}

# Fetch in decade chunks — USGS caps single requests at 20,000 events
DECADES = [
    ("1950-01-01", "1960-01-01"),
    ("1960-01-01", "1970-01-01"),
    ("1970-01-01", "1980-01-01"),
    ("1980-01-01", "1990-01-01"),
    ("1990-01-01", "2000-01-01"),
    ("2000-01-01", "2010-01-01"),
    ("2010-01-01", "2020-01-01"),
    ("2020-01-01", "2025-01-01"),
]

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def fetch_decade(start, end):
    params = {
        "format":       "geojson",
        "starttime":    start,
        "endtime":      end,
        "minmagnitude": 5.0,
        "orderby":      "time-asc",
        **JAPAN_BBOX,
    }
    print(f"  Fetching {start} → {end} ...", end=" ", flush=True)
    r = requests.get(BASE_URL, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    count = data["metadata"]["count"]
    print(f"{count} events")
    return data["features"]


def parse_event(feature):
    p = feature["properties"]
    coords = feature["geometry"]["coordinates"]  # [lon, lat, depth]
    return {
        "id":        feature["id"],
        "time":      datetime.utcfromtimestamp(p["time"] / 1000).strftime("%Y-%m-%dT%H:%M:%S"),
        "year":      datetime.utcfromtimestamp(p["time"] / 1000).year,
        "decade":    (datetime.utcfromtimestamp(p["time"] / 1000).year // 10) * 10,
        "magnitude": p["mag"],
        "depth_km":  round(coords[2], 1),
        "lat":       round(coords[1], 4),
        "lon":       round(coords[0], 4),
        "place":     p.get("place", ""),
        "tsunami":   bool(p.get("tsunami", 0)),
        "alert":     p.get("alert"),        # green / yellow / orange / red
        "sig":       p.get("sig", 0),       # significance score 0-1000
        "felt":      p.get("felt", 0),      # number of felt reports
        "cdi":       p.get("cdi"),          # community internet intensity
        "mmi":       p.get("mmi"),          # shaking intensity
        "status":    p.get("status"),       # reviewed / automatic
        "type":      p.get("type", "earthquake"),
    }


def main():
    all_events = []
    for start, end in DECADES:
        try:
            features = fetch_decade(start, end)
            for f in features:
                all_events.append(parse_event(f))
            time.sleep(1)   # be polite to USGS
        except Exception as e:
            print(f"  ERROR: {e}")

    out_path = "data/earthquakes_raw.json"
    with open(out_path, "w") as f:
        json.dump(all_events, f, indent=2)

    print(f"\n✓ Saved {len(all_events)} events to {out_path}")

    # Quick summary
    mags = [e["magnitude"] for e in all_events if e["magnitude"]]
    tsunamis = sum(1 for e in all_events if e["tsunami"])
    print(f"  Magnitude range : {min(mags):.1f} – {max(mags):.1f}")
    print(f"  Tsunami-flagged : {tsunamis}")
    print(f"  Decades covered : {DECADES[0][0][:4]} – {DECADES[-1][1][:4]}")


if __name__ == "__main__":
    main()
