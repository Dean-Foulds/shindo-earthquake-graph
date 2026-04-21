from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db

client = TestClient(app)

FAKE_ROWS = [
    {
        "fault_id": "japan_trench",
        "fault_name": "Japan Trench",
        "fault_type": "subduction",
        "predicted_max_mag": 9.1,
        "last_major_year": 2011,
        "total_events": 50,
        "years_m6": [1960, 1978, 1994, 2003, 2011],
        "years_m7": [1978, 2003, 2011],
        "years_m8": [2011],
        "rate_per_year": 0.77,
    },
    {
        "fault_id": "nankai_trough",
        "fault_name": "Nankai Trough",
        "fault_type": "subduction",
        "predicted_max_mag": 9.1,
        "last_major_year": 1946,
        "total_events": 10,
        "years_m6": [1944, 1946],
        "years_m7": [1944],
        "years_m8": [],
        "rate_per_year": 0.13,
    },
]


class MockAnalysisDb:
    def cypher_read(self, query, params=None):
        return FAKE_ROWS


def test_predict_shape():
    app.dependency_overrides[get_db] = lambda: MockAnalysisDb()
    response = client.get("/analysis/predict")
    assert response.status_code == 200
    data = response.json()
    assert "fault_zones" in data
    assert "ranked_by_overdue" in data
    assert "disclaimer" in data
    assert "data_range" in data
    assert len(data["fault_zones"]) == 2


def test_predict_tiers():
    app.dependency_overrides[get_db] = lambda: MockAnalysisDb()
    response = client.get("/analysis/predict")
    data = response.json()
    fz = data["fault_zones"][0]
    assert "tiers" in fz
    assert "m6" in fz["tiers"]
    assert "m7" in fz["tiers"]
    assert "m8" in fz["tiers"]
    assert fz["tiers"]["m6"]["event_count"] == 5
    assert fz["tiers"]["m6"]["sample_size_warning"] is False


def test_predict_sample_warning():
    app.dependency_overrides[get_db] = lambda: MockAnalysisDb()
    response = client.get("/analysis/predict")
    data = response.json()
    nankai = next(fz for fz in data["fault_zones"] if fz["fault_id"] == "nankai_trough")
    assert nankai["tiers"]["m8"]["sample_size_warning"] is True
    assert nankai["tiers"]["m7"]["sample_size_warning"] is True


def teardown_function():
    app.dependency_overrides = {}
