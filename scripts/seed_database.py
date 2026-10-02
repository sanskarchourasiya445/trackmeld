"""
TrackMeld Phase 1 — Database Seeding Script.

Orchestrates migration verification, idempotent Phase 0 reference ingestion,
and confirms target database state.
"""

import sys
import logging
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.ingest_phase0 import run_ingestion
from sqlalchemy import text
from backend.app.db.session import sync_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_database")


def seed():
    logger.info("Executing TrackMeld database seed process...")
    # 1. Run deterministic ingestion
    run_ingestion()

    # 2. Verify row counts
    tables = [
        ("source_documents", 18),
        ("stations", 68),
        ("sections", 66),
        ("trains", 3429),
        ("train_movements", 82),
        ("railway_rules", 9),
        ("infrastructure_specs", 3),
        ("corridors", 4),
    ]

    with sync_engine.connect() as conn:
        all_matched = True
        for table, expected in tables:
            res = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            status = "MATCH" if res == expected else "MISMATCH"
            logger.info("Seed Check: %-22s expected=%d actual=%d [%s]", table, expected, res, status)
            if res != expected:
                all_matched = False

    if not all_matched:
        logger.error("Seeding count check failed!")
        sys.exit(1)

    logger.info("Database seeding successfully verified against Phase 0 reference foundation.")


if __name__ == "__main__":
    seed()
