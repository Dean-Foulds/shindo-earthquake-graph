"""
SHINDO — Static reference data
================================
Fault zones, nuclear facilities, and prefectures.
This module is imported by 02_build_graph.py — do not run directly.

Sources:
  Fault zones     : GSJ Active Fault Database, HERP (2013)
  Nuclear plants  : IAEA PRIS (Power Reactor Information System)
  Prefectures     : Ministry of Land, Infrastructure, Transport and Tourism
"""


# ──────────────────────────────────────────────────────────────────
# FAULT ZONES
# Each zone has a geographic bounding polygon (simplified bbox)
# used to assign earthquakes to their source fault.
# Priority order matters: more specific zones checked first.
# ──────────────────────────────────────────────────────────────────

FAULT_ZONES = [
    {
        "id":            "nankai_trough",
        "name":          "Nankai Trough",
        "type":          "subduction",
        "plates":        "Philippine Sea / Eurasian",
        "predicted_max_mag": 9.1,
        "last_major_year":   1946,
        "description":   "Megathrust fault. M8-9 predicted within 30 years. Threatens Tokai, Kinki, Shikoku.",
        # lat_min, lat_max, lon_min, lon_max, depth_max
        "bbox": (32.0, 35.5, 132.5, 138.5, 60),
    },
    {
        "id":            "japan_trench",
        "name":          "Japan Trench",
        "type":          "subduction",
        "plates":        "Pacific / North American",
        "predicted_max_mag": 9.1,
        "last_major_year":   2011,
        "description":   "Source of 2011 Tohoku M9.1. Runs along Pacific coast of Honshu and Hokkaido.",
        "bbox": (35.0, 45.0, 140.0, 146.0, 80),
    },
    {
        "id":            "sagami_trough",
        "name":          "Sagami Trough",
        "type":          "subduction",
        "plates":        "Philippine Sea / North American",
        "predicted_max_mag": 8.0,
        "last_major_year":   1923,
        "description":   "Source of 1923 Great Kanto earthquake (M7.9, ~142,000 deaths).",
        "bbox": (34.0, 36.5, 138.5, 141.5, 50),
    },
    {
        "id":            "ryukyu_trench",
        "name":          "Ryukyu Trench",
        "type":          "subduction",
        "plates":        "Philippine Sea / Eurasian",
        "predicted_max_mag": 8.0,
        "last_major_year":   1771,
        "description":   "Runs southwest of Kyushu through Okinawa. Tsunami risk for southwest Japan.",
        "bbox": (24.0, 32.5, 122.0, 132.5, 60),
    },
    {
        "id":            "median_tectonic_line",
        "name":          "Median Tectonic Line",
        "type":          "strike_slip",
        "plates":        "intraplate",
        "predicted_max_mag": 8.0,
        "last_major_year":   1596,
        "description":   "Japan's longest active fault. Runs east-west across Honshu and Shikoku.",
        "bbox": (33.0, 36.5, 130.5, 137.0, 30),
    },
    {
        "id":            "noto_peninsula",
        "name":          "Noto Peninsula fault system",
        "type":          "reverse",
        "plates":        "intraplate",
        "predicted_max_mag": 7.6,
        "last_major_year":   2024,
        "description":   "Source of January 2024 Noto M7.5 earthquake. Poorly understood prior.",
        "bbox": (36.5, 38.0, 136.0, 138.0, 20),
    },
    {
        "id":            "itoigawa_shizuoka",
        "name":          "Itoigawa-Shizuoka Tectonic Line",
        "type":          "strike_slip",
        "plates":        "intraplate",
        "predicted_max_mag": 8.0,
        "last_major_year":   None,
        "description":   "Major boundary dividing northeast and southwest Japan geology.",
        "bbox": (35.0, 37.5, 137.5, 139.0, 25),
    },
    {
        "id":            "intraplate_generic",
        "name":          "Intraplate (crustal)",
        "type":          "crustal",
        "plates":        "intraplate",
        "predicted_max_mag": 7.5,
        "last_major_year":   None,
        "description":   "Shallow crustal earthquakes not on a mapped major fault. Includes Kobe 1995.",
        "bbox": (24.0, 46.0, 122.0, 148.0, 30),   # catch-all for shallow
    },
    {
        "id":            "deep_slab",
        "name":          "Deep slab (intraslab)",
        "type":          "intraslab",
        "plates":        "Pacific slab",
        "predicted_max_mag": 7.8,
        "last_major_year":   2003,
        "description":   "Deep earthquakes within the subducting Pacific slab. Less tsunami risk.",
        "bbox": (24.0, 46.0, 122.0, 148.0, 700),  # catch-all for deep
    },
]


def assign_fault_zone(lat, lon, depth):
    """Return fault zone id for a given earthquake location."""
    # Priority zones checked first (order in list matters)
    priority = [
        "nankai_trough", "japan_trench", "sagami_trough",
        "ryukyu_trench", "noto_peninsula", "median_tectonic_line",
        "itoigawa_shizuoka",
    ]
    for zone_id in priority:
        zone = next(z for z in FAULT_ZONES if z["id"] == zone_id)
        lmin, lmax, omin, omax, dmax = zone["bbox"]
        if lmin <= lat <= lmax and omin <= lon <= omax and depth <= dmax:
            return zone_id

    if depth <= 30:
        return "intraplate_generic"
    return "deep_slab"


# ──────────────────────────────────────────────────────────────────
# NUCLEAR FACILITIES  (IAEA PRIS, as of 2024)
# ──────────────────────────────────────────────────────────────────

NUCLEAR_FACILITIES = [
    {"id": "fukushima_daiichi", "name": "Fukushima Daiichi",   "prefecture": "Fukushima",  "lat": 37.421, "lon": 141.032, "reactors": 6, "status": "decommissioning", "operator": "TEPCO",   "note": "Meltdown 2011"},
    {"id": "fukushima_daini",   "name": "Fukushima Daini",     "prefecture": "Fukushima",  "lat": 37.316, "lon": 141.025, "reactors": 4, "status": "shutdown",        "operator": "TEPCO",   "note": "Shut post-2011"},
    {"id": "onagawa",           "name": "Onagawa",             "prefecture": "Miyagi",     "lat": 38.401, "lon": 141.498, "reactors": 3, "status": "restarting",      "operator": "Tohoku",  "note": "Survived 2011"},
    {"id": "tokai_daini",       "name": "Tokai Daini",         "prefecture": "Ibaraki",    "lat": 36.466, "lon": 140.607, "reactors": 1, "status": "suspended",       "operator": "JAPC",    "note": "Near Tokyo"},
    {"id": "kashiwazaki_kariwa","name": "Kashiwazaki-Kariwa",  "prefecture": "Niigata",    "lat": 37.430, "lon": 138.602, "reactors": 7, "status": "suspended",       "operator": "TEPCO",   "note": "World's largest"},
    {"id": "shika",             "name": "Shika",               "prefecture": "Ishikawa",   "lat": 37.006, "lon": 136.689, "reactors": 2, "status": "suspended",       "operator": "Hokuriku","note": "Near 2024 Noto quake"},
    {"id": "mihama",            "name": "Mihama",              "prefecture": "Fukui",      "lat": 35.703, "lon": 135.994, "reactors": 3, "status": "active",          "operator": "Kansai",  "note": "Oldest active in Japan"},
    {"id": "ohi",               "name": "Ohi",                 "prefecture": "Fukui",      "lat": 35.540, "lon": 135.655, "reactors": 4, "status": "active",          "operator": "Kansai",  "note": ""},
    {"id": "takahama",          "name": "Takahama",            "prefecture": "Fukui",      "lat": 35.523, "lon": 135.508, "reactors": 4, "status": "active",          "operator": "Kansai",  "note": ""},
    {"id": "hamaoka",           "name": "Hamaoka",             "prefecture": "Shizuoka",   "lat": 34.624, "lon": 138.143, "reactors": 5, "status": "suspended",       "operator": "Chubu",   "note": "Directly above Nankai Trough"},
    {"id": "shimane",           "name": "Shimane",             "prefecture": "Shimane",    "lat": 35.535, "lon": 132.993, "reactors": 3, "status": "restarting",      "operator": "Chugoku", "note": ""},
    {"id": "ikata",             "name": "Ikata",               "prefecture": "Ehime",      "lat": 33.493, "lon": 132.312, "reactors": 3, "status": "active",          "operator": "Shikoku", "note": "On Median Tectonic Line"},
    {"id": "genkai",            "name": "Genkai",              "prefecture": "Saga",       "lat": 33.518, "lon": 129.836, "reactors": 4, "status": "active",          "operator": "Kyushu",  "note": ""},
    {"id": "sendai_npp",        "name": "Sendai",              "prefecture": "Kagoshima",  "lat": 31.833, "lon": 130.194, "reactors": 2, "status": "active",          "operator": "Kyushu",  "note": "First restart post-2011"},
    {"id": "tomari",            "name": "Tomari",              "prefecture": "Hokkaido",   "lat": 43.046, "lon": 140.526, "reactors": 3, "status": "suspended",       "operator": "Hokkaido","note": ""},
]


# ──────────────────────────────────────────────────────────────────
# PREFECTURES  (47 total, with region and coastline metadata)
# coast_type: pacific | sea_of_japan | both | inland | pacific_tsunami_risk
# ──────────────────────────────────────────────────────────────────

PREFECTURES = [
    # Hokkaido
    {"id": "hokkaido",   "name": "Hokkaido",   "region": "Hokkaido",  "lat": 43.06, "lon": 141.35, "coast": "both",             "population_m": 5.2},
    # Tohoku
    {"id": "aomori",     "name": "Aomori",     "region": "Tohoku",    "lat": 40.82, "lon": 140.74, "coast": "both",             "population_m": 1.2},
    {"id": "iwate",      "name": "Iwate",      "region": "Tohoku",    "lat": 39.70, "lon": 141.15, "coast": "pacific",          "population_m": 1.2},
    {"id": "miyagi",     "name": "Miyagi",     "region": "Tohoku",    "lat": 38.27, "lon": 140.87, "coast": "pacific",          "population_m": 2.3},
    {"id": "akita",      "name": "Akita",      "region": "Tohoku",    "lat": 39.72, "lon": 140.10, "coast": "sea_of_japan",     "population_m": 1.0},
    {"id": "yamagata",   "name": "Yamagata",   "region": "Tohoku",    "lat": 38.24, "lon": 140.36, "coast": "sea_of_japan",     "population_m": 1.1},
    {"id": "fukushima",  "name": "Fukushima",  "region": "Tohoku",    "lat": 37.75, "lon": 140.47, "coast": "pacific",          "population_m": 1.8},
    # Kanto
    {"id": "ibaraki",    "name": "Ibaraki",    "region": "Kanto",     "lat": 36.34, "lon": 140.45, "coast": "pacific",          "population_m": 2.9},
    {"id": "tochigi",    "name": "Tochigi",    "region": "Kanto",     "lat": 36.57, "lon": 139.88, "coast": "inland",           "population_m": 2.0},
    {"id": "gunma",      "name": "Gunma",      "region": "Kanto",     "lat": 36.39, "lon": 139.06, "coast": "inland",           "population_m": 2.0},
    {"id": "saitama",    "name": "Saitama",    "region": "Kanto",     "lat": 35.86, "lon": 139.65, "coast": "inland",           "population_m": 7.3},
    {"id": "chiba",      "name": "Chiba",      "region": "Kanto",     "lat": 35.61, "lon": 140.12, "coast": "pacific",          "population_m": 6.3},
    {"id": "tokyo",      "name": "Tokyo",      "region": "Kanto",     "lat": 35.69, "lon": 139.69, "coast": "pacific",          "population_m": 13.9},
    {"id": "kanagawa",   "name": "Kanagawa",   "region": "Kanto",     "lat": 35.45, "lon": 139.64, "coast": "pacific",          "population_m": 9.2},
    # Chubu
    {"id": "niigata",    "name": "Niigata",    "region": "Chubu",     "lat": 37.90, "lon": 139.02, "coast": "sea_of_japan",     "population_m": 2.2},
    {"id": "toyama",     "name": "Toyama",     "region": "Chubu",     "lat": 36.70, "lon": 137.21, "coast": "sea_of_japan",     "population_m": 1.0},
    {"id": "ishikawa",   "name": "Ishikawa",   "region": "Chubu",     "lat": 36.59, "lon": 136.63, "coast": "sea_of_japan",     "population_m": 1.1},
    {"id": "fukui",      "name": "Fukui",      "region": "Chubu",     "lat": 36.06, "lon": 136.22, "coast": "sea_of_japan",     "population_m": 0.8},
    {"id": "yamanashi",  "name": "Yamanashi",  "region": "Chubu",     "lat": 35.66, "lon": 138.57, "coast": "inland",           "population_m": 0.8},
    {"id": "nagano",     "name": "Nagano",     "region": "Chubu",     "lat": 36.65, "lon": 138.19, "coast": "inland",           "population_m": 2.1},
    {"id": "gifu",       "name": "Gifu",       "region": "Chubu",     "lat": 35.39, "lon": 136.72, "coast": "inland",           "population_m": 2.0},
    {"id": "shizuoka",   "name": "Shizuoka",   "region": "Chubu",     "lat": 34.98, "lon": 138.38, "coast": "pacific",          "population_m": 3.6},
    {"id": "aichi",      "name": "Aichi",      "region": "Chubu",     "lat": 35.18, "lon": 137.10, "coast": "pacific",          "population_m": 7.5},
    # Kinki
    {"id": "mie",        "name": "Mie",        "region": "Kinki",     "lat": 34.73, "lon": 136.51, "coast": "pacific",          "population_m": 1.8},
    {"id": "shiga",      "name": "Shiga",      "region": "Kinki",     "lat": 35.00, "lon": 135.87, "coast": "inland",           "population_m": 1.4},
    {"id": "kyoto",      "name": "Kyoto",      "region": "Kinki",     "lat": 35.02, "lon": 135.76, "coast": "sea_of_japan",     "population_m": 2.6},
    {"id": "osaka",      "name": "Osaka",      "region": "Kinki",     "lat": 34.69, "lon": 135.50, "coast": "pacific",          "population_m": 8.8},
    {"id": "hyogo",      "name": "Hyogo",      "region": "Kinki",     "lat": 34.69, "lon": 135.18, "coast": "both",             "population_m": 5.5},
    {"id": "nara",       "name": "Nara",       "region": "Kinki",     "lat": 34.69, "lon": 135.83, "coast": "inland",           "population_m": 1.3},
    {"id": "wakayama",   "name": "Wakayama",   "region": "Kinki",     "lat": 34.23, "lon": 135.17, "coast": "pacific",          "population_m": 0.9},
    # Chugoku
    {"id": "tottori",    "name": "Tottori",    "region": "Chugoku",   "lat": 35.50, "lon": 134.24, "coast": "sea_of_japan",     "population_m": 0.6},
    {"id": "shimane",    "name": "Shimane",    "region": "Chugoku",   "lat": 35.47, "lon": 133.06, "coast": "sea_of_japan",     "population_m": 0.7},
    {"id": "okayama",    "name": "Okayama",    "region": "Chugoku",   "lat": 34.66, "lon": 133.93, "coast": "pacific",          "population_m": 1.9},
    {"id": "hiroshima",  "name": "Hiroshima",  "region": "Chugoku",   "lat": 34.40, "lon": 132.46, "coast": "pacific",          "population_m": 2.8},
    {"id": "yamaguchi",  "name": "Yamaguchi",  "region": "Chugoku",   "lat": 34.19, "lon": 131.47, "coast": "both",             "population_m": 1.3},
    # Shikoku
    {"id": "tokushima",  "name": "Tokushima",  "region": "Shikoku",   "lat": 34.07, "lon": 134.55, "coast": "pacific",          "population_m": 0.7},
    {"id": "kagawa",     "name": "Kagawa",     "region": "Shikoku",   "lat": 34.34, "lon": 134.04, "coast": "pacific",          "population_m": 1.0},
    {"id": "ehime",      "name": "Ehime",      "region": "Shikoku",   "lat": 33.84, "lon": 132.77, "coast": "pacific",          "population_m": 1.4},
    {"id": "kochi",      "name": "Kochi",      "region": "Shikoku",   "lat": 33.56, "lon": 133.53, "coast": "pacific",          "population_m": 0.7},
    # Kyushu
    {"id": "fukuoka",    "name": "Fukuoka",    "region": "Kyushu",    "lat": 33.61, "lon": 130.42, "coast": "both",             "population_m": 5.1},
    {"id": "saga",       "name": "Saga",       "region": "Kyushu",    "lat": 33.25, "lon": 130.30, "coast": "both",             "population_m": 0.8},
    {"id": "nagasaki",   "name": "Nagasaki",   "region": "Kyushu",    "lat": 32.74, "lon": 129.87, "coast": "both",             "population_m": 1.3},
    {"id": "kumamoto",   "name": "Kumamoto",   "region": "Kyushu",    "lat": 32.79, "lon": 130.74, "coast": "pacific",          "population_m": 1.8},
    {"id": "oita",       "name": "Oita",       "region": "Kyushu",    "lat": 33.24, "lon": 131.61, "coast": "pacific",          "population_m": 1.1},
    {"id": "miyazaki",   "name": "Miyazaki",   "region": "Kyushu",    "lat": 31.91, "lon": 131.42, "coast": "pacific",          "population_m": 1.1},
    {"id": "kagoshima",  "name": "Kagoshima",  "region": "Kyushu",    "lat": 31.56, "lon": 130.56, "coast": "pacific",          "population_m": 1.6},
    # Okinawa
    {"id": "okinawa",    "name": "Okinawa",    "region": "Okinawa",   "lat": 26.21, "lon": 127.68, "coast": "pacific",          "population_m": 1.5},
]


# ──────────────────────────────────────────────────────────────────
# NOTABLE HISTORICAL EVENTS  (enriched metadata on landmark quakes)
# ──────────────────────────────────────────────────────────────────

NOTABLE_EVENTS = {
    # USGS event id → enriched fields
    # These will be merged into earthquake nodes at load time
    "usp000d6vk": {"name": "2011 Tohoku",      "deaths": 15897, "missing": 2533, "injured": 6157,  "nuclear_incident": True,  "tsunami_max_height_m": 40.5},
    "usp000cfz9": {"name": "1995 Kobe",         "deaths": 6434,  "missing": 0,    "injured": 43792, "nuclear_incident": False, "tsunami_max_height_m": None},
    "usp00004ht": {"name": "1923 Great Kanto",  "deaths": 142807,"missing": 0,    "injured": 0,     "nuclear_incident": False, "tsunami_max_height_m": 12.0},
    "usp000e3wq": {"name": "2016 Kumamoto",     "deaths": 273,   "missing": 0,    "injured": 2809,  "nuclear_incident": False, "tsunami_max_height_m": None},
    "usp000hvnd": {"name": "2024 Noto",         "deaths": 241,   "missing": 0,    "injured": 1491,  "nuclear_incident": False, "tsunami_max_height_m": 4.0},
}
