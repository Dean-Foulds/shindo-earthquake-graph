DEFINITION = {
    "name": "get_jma_warning_level",
    "description": (
        "Applies JMA published rules to determine what tsunami warning "
        "level would be issued for a given offshore earthquake. "
        "Only relevant when sea_floor_depth is negative (offshore). "
        "Returns warning level in Japanese and English."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "magnitude": {
                "type": "number",
                "description": "Moment magnitude of the earthquake"
            },
            "sea_floor_depth": {
                "type": "number",
                "description": "Sea floor depth in metres from GEBCO. Negative = offshore."
            }
        },
        "required": ["magnitude", "sea_floor_depth"]
    }
}

async def get_jma_warning_level(magnitude: float,
                                 sea_floor_depth: float) -> dict:
    if sea_floor_depth >= 0:
        return {
            "warning_issued"     : False,
            "reason"             : "Onshore event — no tsunami risk",
            "warning_level_ja"   : None,
            "warning_level_en"   : None,
            "expected_wave_range": None,
        }
    if magnitude >= 8.0:
        return {
            "warning_issued"     : True,
            "warning_level_ja"   : "大津波警報",
            "warning_level_en"   : "Major Tsunami Warning",
            "expected_wave_range": "Over 3m",
            "minutes_to_issue"   : 3,
        }
    elif magnitude >= 7.0:
        return {
            "warning_issued"     : True,
            "warning_level_ja"   : "津波警報",
            "warning_level_en"   : "Tsunami Warning",
            "expected_wave_range": "1m - 3m",
            "minutes_to_issue"   : 3,
        }
    elif magnitude >= 6.0:
        return {
            "warning_issued"     : True,
            "warning_level_ja"   : "津波注意報",
            "warning_level_en"   : "Tsunami Advisory",
            "expected_wave_range": "Under 1m",
            "minutes_to_issue"   : 3,
        }
    return {
        "warning_issued"     : False,
        "reason"             : "Magnitude below tsunami threshold (M6.0)",
        "warning_level_ja"   : None,
        "warning_level_en"   : None,
        "expected_wave_range": None,
    }
