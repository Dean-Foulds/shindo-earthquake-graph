class MockNeo4jService:
    def run(self, query, **params):
        # Return fake deterministic data
        return [
            {"id": "eq1", "magnitude": 7.5, "place": "Tokyo"},
            {"id": "eq2", "magnitude": 6.8, "place": "Osaka"},
        ]