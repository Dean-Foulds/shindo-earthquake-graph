from fastapi import APIRouter, Depends
from .db import get_db, Neo4jService

router = APIRouter()

@router.get("/earthquakes")
def get_earthquakes(limit: int = 10, db: Neo4jService = Depends(get_db)):
    return db.run(
        "MATCH (e:Earthquake) RETURN e.id AS id LIMIT $limit",
        limit=limit
    )