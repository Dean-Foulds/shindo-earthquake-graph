class MockNeo4jService:
    async def run(self, query, **params):
        return [
            {"id": "eq1", "magnitude": 7.5, "place": "Tokyo"},
            {"id": "eq2", "magnitude": 6.8, "place": "Osaka"},
        ]