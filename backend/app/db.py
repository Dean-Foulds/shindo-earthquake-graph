import os
from neo4j import GraphDatabase

class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

    def run(self, query, **params):
        with self.driver.session() as session:
            return [r.data() for r in session.run(query, **params)]


def get_db():
    return Neo4jService()