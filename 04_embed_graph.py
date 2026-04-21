"""
SHINDO — Step 4: Generate vector embeddings for graph nodes
============================================================
Embeds Earthquake, FaultZone, NuclearFacility, and Prefecture nodes
using Voyage AI (Anthropic's recommended embedding partner).

Stores embeddings as an `embedding` property on each node and creates
Neo4j vector indexes so the AURA agent can do similarity search.

Install:
    pip install voyageai

Env vars (add to .env):
    VOYAGE_API_KEY=<your voyage key — free tier at voyageai.com>
    NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD

Usage:
    python 04_embed_graph.py                    # embed all node types
    python 04_embed_graph.py --type earthquake  # only earthquakes
    python 04_embed_graph.py --dry-run          # preview text, no API calls
    python 04_embed_graph.py --limit 50         # embed first 50 per type
"""

import os
import sys
import time
import json
import math
import argparse
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

VOYAGE_MODEL    = "voyage-3"   # 1024-dim, best general quality
EMBED_DIM       = 1024
BATCH_SIZE      = 96           # Voyage max ~128; stay comfortable
RATE_LIMIT_WAIT = 0.5          # standard tier: no meaningful wait needed
PROGRESS_FILE   = ".embed_progress.json"

# ── Text builders ─────────────────────────────────────────────────

def earthquake_text(eq: dict) -> str:
    """Build a rich natural-language description of an earthquake node."""
    parts = [
        f"M{eq.get('magnitude', '?')} earthquake",
    ]
    if eq.get("place"):
        parts.append(f"near {eq['place']}")
    if eq.get("fault_zone"):
        parts.append(f"on the {eq['fault_zone']} fault zone")
    parts.append(f"(depth {eq.get('depth_km', '?')} km, year {eq.get('year', '?')})")

    if eq.get("tsunami"):
        h = eq.get("tsunami_max_height_m")
        parts.append(f"Triggered a tsunami" + (f" reaching {h} m" if h else "") + ".")

    deaths = eq.get("deaths")
    if deaths:
        parts.append(f"Caused approximately {deaths:,} deaths.")

    sig = eq.get("sig")
    if sig and sig > 500:
        parts.append(f"High seismic significance score: {sig}.")

    name = eq.get("name")
    if name:
        parts.append(f"Known as the {name}.")

    nuclear = eq.get("nuclear_incident")
    if nuclear:
        parts.append("Caused a nuclear facility incident.")

    return " ".join(parts)


def fault_zone_text(fz: dict) -> str:
    parts = [
        f"{fz['name']} is a {fz['type']} fault zone",
        f"between the {fz.get('plates', 'unknown')} plates.",
    ]
    if fz.get("description"):
        parts.append(fz["description"])
    mm = fz.get("predicted_max_mag")
    if mm:
        parts.append(f"Predicted maximum magnitude: M{mm}.")
    ly = fz.get("last_major_year")
    if ly:
        parts.append(f"Last major event: {ly}.")
    return " ".join(parts)


def nuclear_text(nf: dict) -> str:
    parts = [
        f"{nf['name']} nuclear power plant in {nf.get('prefecture', '?')} prefecture.",
        f"Current status: {nf.get('status', 'unknown')}.",
        f"{nf.get('reactors', '?')} reactors operated by {nf.get('operator', 'unknown')}.",
    ]
    note = nf.get("note", "")
    if note:
        parts.append(note + ".")
    return " ".join(parts)


def prefecture_text(pf: dict) -> str:
    parts = [
        f"{pf['name']} prefecture in {pf.get('region', '?')} region of Japan.",
        f"Population: {pf.get('population_m', '?')} million.",
        f"Coastline: {pf.get('coast', 'unknown')}.",
        f"Located at {pf.get('lat', '?')}°N, {pf.get('lon', '?')}°E.",
    ]
    return " ".join(parts)


def tsunami_text(ts: dict) -> str:
    parts = [f"Tsunami event in {ts.get('year', '?')}"]
    h = ts.get("max_height_m")
    if h:
        parts.append(f"with maximum wave height {h} m")
    mag = ts.get("source_mag")
    if mag:
        parts.append(f"triggered by a M{mag} earthquake")
    cause = ts.get("cause")
    if cause:
        parts.append(f"Cause: {cause}.")
    deaths = ts.get("deaths")
    if deaths:
        parts.append(f"Caused approximately {deaths:,} deaths.")
    return " ".join(parts) + "."


# ── Neo4j helpers ─────────────────────────────────────────────────

def neo4j_driver():
    from neo4j import GraphDatabase
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def create_vector_indexes(driver):
    """Create Neo4j vector indexes for all embedded node types."""
    indexes = [
        ("earthquake_embedding", "Earthquake"),
        ("fault_zone_embedding", "FaultZone"),
        ("nuclear_embedding",    "NuclearFacility"),
        ("prefecture_embedding", "Prefecture"),
        ("tsunami_embedding",    "Tsunami"),
    ]
    with driver.session() as s:
        for idx_name, label in indexes:
            s.run(f"""
                CREATE VECTOR INDEX {idx_name} IF NOT EXISTS
                FOR (n:{label}) ON n.embedding
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {EMBED_DIM},
                    `vector.similarity_function`: 'cosine'
                }}}}
            """)
            print(f"  ✓ Vector index ready: {idx_name} ({label})")


def fetch_earthquakes(driver, limit=None):
    q = """
        MATCH (e:Earthquake)
        OPTIONAL MATCH (e)-[:ORIGINATED_ON]->(fz:FaultZone)
        OPTIONAL MATCH (e)-[:TRIGGERED]->(t:Tsunami)
        RETURN e {
            .id, .magnitude, .depth_km, .year, .place,
            .tsunami, .deaths, .sig, .name, .nuclear_incident,
            fault_zone: fz.name,
            tsunami_max_height_m: t.max_height_m
        } AS eq
        """ + (f"LIMIT {limit}" if limit else "")
    with driver.session() as s:
        return [r["eq"] for r in s.run(q)]


def fetch_fault_zones(driver):
    with driver.session() as s:
        return [dict(r["fz"]) for r in s.run(
            "MATCH (fz:FaultZone) RETURN fz"
        )]


def fetch_nuclear(driver):
    with driver.session() as s:
        return [dict(r["nf"]) for r in s.run(
            "MATCH (nf:NuclearFacility) RETURN nf"
        )]


def fetch_prefectures(driver):
    with driver.session() as s:
        return [dict(r["pf"]) for r in s.run(
            "MATCH (pf:Prefecture) RETURN pf"
        )]


def fetch_tsunamis(driver):
    with driver.session() as s:
        return [dict(r["ts"]) for r in s.run(
            "MATCH (ts:Tsunami) RETURN ts"
        )]


def write_embeddings(driver, label, id_field, records_with_embeddings):
    """Batch-write embedding vectors back to Neo4j nodes."""
    q = f"""
        UNWIND $rows AS row
        MATCH (n:{label} {{{id_field}: row.id}})
        SET n.embedding = row.embedding,
            n.embedding_text = row.text
    """
    with driver.session() as s:
        s.run(q, rows=records_with_embeddings)


# ── Voyage AI embeddings ──────────────────────────────────────────

def embed_texts(texts: list[str], dry_run=False) -> list[list[float]]:
    """Call Voyage AI with retry/backoff. Returns zeros in dry-run mode."""
    if dry_run:
        return [[0.0] * EMBED_DIM for _ in texts]

    import voyageai
    vo = voyageai.Client(api_key=VOYAGE_API_KEY)
    for attempt in range(6):
        try:
            result = vo.embed(texts, model=VOYAGE_MODEL, input_type="document")
            return result.embeddings
        except Exception as e:
            msg = str(e).lower()
            if "rate" in msg or "429" in msg:
                wait = RATE_LIMIT_WAIT * (2 ** attempt)
                print(f"\n  ⏳ Rate limited — waiting {wait:.0f}s…", end="", flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Exceeded retry limit")


def load_progress(label: str) -> set:
    """Return set of already-embedded node IDs from progress file."""
    try:
        with open(PROGRESS_FILE) as f:
            return set(json.load(f).get(label, []))
    except FileNotFoundError:
        return set()


def save_progress(label: str, done_ids: set):
    try:
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    data[label] = list(done_ids)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)


def embed_nodes(driver, label, id_field, records, text_fn, dry_run=False, limit=None):
    """Embed a list of node dicts and write back to Neo4j. Resumes from progress file."""
    if limit:
        records = records[:limit]

    # Skip already-embedded nodes (resume support)
    done_ids = load_progress(label) if not dry_run else set()
    pending = [r for r in records if (r.get(id_field) or r.get("id")) not in done_ids]

    total_all = len(records)
    total = len(pending)
    skipped = total_all - total
    print(f"\n  {label}: {total} to embed" + (f" ({skipped} already done, resuming)" if skipped else ""))

    if total == 0:
        print(f"  ✓ All {label} nodes already embedded")
        return []

    all_rows = []
    for i in range(0, total, BATCH_SIZE):
        batch = pending[i:i+BATCH_SIZE]
        texts = [text_fn(r) for r in batch]

        if dry_run and i == 0:
            print(f"\n  [DRY RUN] Sample text for first {label} node:")
            print(f"  {texts[0]}\n")

        embeddings = embed_texts(texts, dry_run=dry_run)

        batch_rows = []
        for rec, text, emb in zip(batch, texts, embeddings):
            node_id = rec.get(id_field) or rec.get("id")
            batch_rows.append({"id": node_id, "text": text, "embedding": emb})
            done_ids.add(node_id)

        # Write each batch immediately so progress is never lost
        if not dry_run:
            write_embeddings(driver, label, id_field, batch_rows)
            save_progress(label, done_ids)

        all_rows.extend(batch_rows)
        pct = min(i + BATCH_SIZE, total) + skipped
        eta_batches = (total - i - BATCH_SIZE) // BATCH_SIZE
        eta_s = eta_batches * RATE_LIMIT_WAIT
        eta_str = f" — ~{eta_s/60:.0f}min remaining" if eta_s > 60 and not dry_run else ""
        print(f"  [{pct}/{total_all}]{eta_str}", end="\r", flush=True)

        if not dry_run and i + BATCH_SIZE < total:
            time.sleep(RATE_LIMIT_WAIT)

    print(f"  [{total_all}/{total_all}] done                              ")

    if dry_run:
        print(f"  [DRY RUN] Would write {len(all_rows)} embeddings")
    else:
        print(f"  ✓ {len(all_rows)} new embeddings written to Neo4j")

    return all_rows


# ── Semantic search helper (also used by AURA agent) ──────────────

def semantic_search(driver, query_text: str, label: str = "Earthquake",
                    top_k: int = 5, dry_run: bool = False):
    """
    Find the top-k most similar nodes to a query string.
    Returns list of {node_id, score, properties}.
    """
    index_map = {
        "Earthquake":      "earthquake_embedding",
        "FaultZone":       "fault_zone_embedding",
        "NuclearFacility": "nuclear_embedding",
        "Prefecture":      "prefecture_embedding",
        "Tsunami":         "tsunami_embedding",
    }
    idx = index_map.get(label, "earthquake_embedding")

    [query_vec] = embed_texts([query_text], dry_run=dry_run)

    with driver.session() as s:
        results = s.run(f"""
            CALL db.index.vector.queryNodes('{idx}', $k, $vec)
            YIELD node, score
            RETURN node, score
            ORDER BY score DESC
        """, k=top_k, vec=query_vec)

        return [
            {"score": round(r["score"], 4), "node": dict(r["node"])}
            for r in results
        ]


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SHINDO — Embed graph nodes")
    parser.add_argument("--type",    choices=["earthquake","faultzone","nuclear","prefecture","tsunami","all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Preview text without calling Voyage AI")
    parser.add_argument("--limit",   type=int, default=None, help="Max nodes per type (useful for testing)")
    parser.add_argument("--search",  type=str, default=None, help="Run a semantic search test after embedding")
    args = parser.parse_args()

    # Validate env vars
    missing = []
    if not NEO4J_URI:      missing.append("NEO4J_URI")
    if not NEO4J_USER:     missing.append("NEO4J_USER")
    if not NEO4J_PASSWORD: missing.append("NEO4J_PASSWORD")
    if not args.dry_run and not VOYAGE_API_KEY:
        missing.append("VOYAGE_API_KEY (get a free key at voyageai.com)")
    if missing:
        print(f"❌  Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    if not args.dry_run:
        try:
            import voyageai
        except ImportError:
            print("❌  voyageai not installed. Run:  pip install voyageai")
            sys.exit(1)

    print("🔌  Connecting to Neo4j…")
    driver = neo4j_driver()

    print("📐  Creating vector indexes…")
    create_vector_indexes(driver)

    run_all = args.type == "all"

    if run_all or args.type == "faultzone":
        fzs = fetch_fault_zones(driver)
        embed_nodes(driver, "FaultZone", "id", fzs, fault_zone_text,
                    dry_run=args.dry_run, limit=args.limit)

    if run_all or args.type == "nuclear":
        nfs = fetch_nuclear(driver)
        embed_nodes(driver, "NuclearFacility", "id", nfs, nuclear_text,
                    dry_run=args.dry_run, limit=args.limit)

    if run_all or args.type == "prefecture":
        pfs = fetch_prefectures(driver)
        embed_nodes(driver, "Prefecture", "id", pfs, prefecture_text,
                    dry_run=args.dry_run, limit=args.limit)

    if run_all or args.type == "tsunami":
        tss = fetch_tsunamis(driver)
        embed_nodes(driver, "Tsunami", "id", tss, tsunami_text,
                    dry_run=args.dry_run, limit=args.limit)

    if run_all or args.type == "earthquake":
        eqs = fetch_earthquakes(driver, limit=args.limit)
        embed_nodes(driver, "Earthquake", "id", eqs, earthquake_text,
                    dry_run=args.dry_run)

    if args.search and not args.dry_run:
        print(f"\n🔍  Semantic search: '{args.search}'")
        results = semantic_search(driver, args.search, label="Earthquake", top_k=5)
        for r in results:
            n = r["node"]
            print(f"  {r['score']:.4f}  M{n.get('magnitude','?')} {n.get('place','?')} ({n.get('year','?')})")

    driver.close()
    print("\n✅  Done.")


if __name__ == "__main__":
    main()
