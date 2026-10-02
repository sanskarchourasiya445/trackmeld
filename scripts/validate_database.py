"""
TrackMeld Phase 1 — Comprehensive Database Validation Suite.

Verifies referential integrity, schema constraints, provenance invariants,
dataset counts, and absence of orphan or duplicate records.
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import text

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.db.session import sync_engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("validate_database")


def run_checks() -> bool:
    checks = []

    def check(category: str, name: str, passed: bool, details: str = ""):
        checks.append((category, name, passed, details))

    with sync_engine.connect() as conn:
        # 1. Source Documents Checks
        n_sources = conn.execute(text("SELECT count(*) FROM source_documents")).scalar()
        check("Source Documents", "Total sources count is >= 18", n_sources >= 18, f"actual={n_sources}")
        n_phase0_sources = conn.execute(text("SELECT count(*) FROM source_documents WHERE source_id != 'SRC-TRACKMELD-SYNTHETIC-GEN'")).scalar()
        check("Source Documents", "Phase 0 official sources count is 18", n_phase0_sources == 18, f"actual={n_phase0_sources}")
        
        dup_sources = conn.execute(
            text("SELECT source_id, count(*) FROM source_documents GROUP BY source_id HAVING count(*) > 1")
        ).fetchall()
        check("Source Documents", "No duplicate source_id", len(dup_sources) == 0, f"dups={len(dup_sources)}")

        null_sources = conn.execute(
            text("SELECT count(*) FROM source_documents WHERE title IS NULL OR sha256 IS NULL OR source_class IS NULL")
        ).scalar()
        check("Source Documents", "Required fields non-null", null_sources == 0, f"nulls={null_sources}")

        # 2. Stations Checks
        n_stn = conn.execute(text("SELECT count(*) FROM stations")).scalar()
        check("Stations", "Count is 68", n_stn == 68, f"actual={n_stn}")

        dup_stn_code = conn.execute(
            text("SELECT station_code, count(*) FROM stations GROUP BY station_code HAVING count(*) > 1")
        ).fetchall()
        check("Stations", "No duplicate station_code", len(dup_stn_code) == 0, f"dups={len(dup_stn_code)}")

        orphan_stn_sources = conn.execute(
            text("SELECT count(*) FROM stations s LEFT JOIN source_documents d ON s.source_id = d.source_id WHERE d.source_id IS NULL")
        ).scalar()
        check("Stations", "All source_id FKs valid", orphan_stn_sources == 0, f"orphans={orphan_stn_sources}")

        stn_real = conn.execute(
            text("SELECT count(*) FROM stations WHERE classification != 'REAL'")
        ).scalar()
        check("Stations", "All stations classified as REAL", stn_real == 0, f"non_real={stn_real}")

        # 3. Sections Checks
        n_sec = conn.execute(text("SELECT count(*) FROM sections")).scalar()
        check("Sections", "Count is 66", n_sec == 66, f"actual={n_sec}")

        dup_sec_code = conn.execute(
            text("SELECT section_code, count(*) FROM sections GROUP BY section_code HAVING count(*) > 1")
        ).fetchall()
        check("Sections", "No duplicate section_code", len(dup_sec_code) == 0, f"dups={len(dup_sec_code)}")

        sec_len = conn.execute(text("SELECT count(*) FROM sections WHERE length_km <= 0")).scalar()
        check("Sections", "All section lengths positive", sec_len == 0, f"non_positive={sec_len}")

        sec_endpoints = conn.execute(text("SELECT count(*) FROM sections WHERE from_station_id = to_station_id")).scalar()
        check("Sections", "Endpoints strictly distinct", sec_endpoints == 0, f"identical={sec_endpoints}")

        orphan_sec_from = conn.execute(
            text("SELECT count(*) FROM sections sec LEFT JOIN stations stn ON sec.from_station_id = stn.station_id WHERE stn.station_id IS NULL")
        ).scalar()
        check("Sections", "All from_station_id FKs valid", orphan_sec_from == 0, f"orphans={orphan_sec_from}")

        orphan_sec_to = conn.execute(
            text("SELECT count(*) FROM sections sec LEFT JOIN stations stn ON sec.to_station_id = stn.station_id WHERE stn.station_id IS NULL")
        ).scalar()
        check("Sections", "All to_station_id FKs valid", orphan_sec_to == 0, f"orphans={orphan_sec_to}")

        sec_derived = conn.execute(
            text("SELECT count(*) FROM sections WHERE classification != 'DERIVED'")
        ).scalar()
        check("Sections", "All sections classified as DERIVED (provenance invariant)", sec_derived == 0, f"non_derived={sec_derived}")

        # 4. Trains Checks
        n_trn = conn.execute(text("SELECT count(*) FROM trains")).scalar()
        check("Trains", "Count is 3429", n_trn == 3429, f"actual={n_trn}")

        dup_trn_num = conn.execute(
            text("SELECT train_number, count(*) FROM trains GROUP BY train_number HAVING count(*) > 1")
        ).fetchall()
        check("Trains", "No duplicate train_number", len(dup_trn_num) == 0, f"dups={len(dup_trn_num)}")

        orphan_trn_src = conn.execute(
            text("SELECT count(*) FROM trains t LEFT JOIN source_documents d ON t.source_id = d.source_id WHERE d.source_id IS NULL")
        ).scalar()
        check("Trains", "All source_id FKs valid", orphan_trn_src == 0, f"orphans={orphan_trn_src}")

        trn_real = conn.execute(
            text("SELECT count(*) FROM trains WHERE classification != 'REAL'")
        ).scalar()
        check("Trains", "All trains classified as REAL", trn_real == 0, f"non_real={trn_real}")

        # 5. Movements Checks
        n_mov = conn.execute(text("SELECT count(*) FROM train_movements")).scalar()
        check("Movements", "Count is 82", n_mov == 82, f"actual={n_mov}")

        dup_mov = conn.execute(
            text("SELECT movement_id, count(*) FROM train_movements GROUP BY movement_id HAVING count(*) > 1")
        ).fetchall()
        check("Movements", "No duplicate movement_id", len(dup_mov) == 0, f"dups={len(dup_mov)}")

        orphan_mov_trn = conn.execute(
            text("SELECT count(*) FROM train_movements m LEFT JOIN trains t ON m.train_id = t.train_id WHERE t.train_id IS NULL")
        ).scalar()
        check("Movements", "All train_id FKs valid", orphan_mov_trn == 0, f"orphans={orphan_mov_trn}")

        orphan_mov_stn = conn.execute(
            text("SELECT count(*) FROM train_movements m LEFT JOIN stations s ON m.station_id = s.station_id WHERE s.station_id IS NULL")
        ).scalar()
        check("Movements", "All station_id FKs valid", orphan_mov_stn == 0, f"orphans={orphan_mov_stn}")

        mov_seq = conn.execute(text("SELECT count(*) FROM train_movements WHERE stop_sequence < 1")).scalar()
        check("Movements", "Stop sequence strictly >= 1", mov_seq == 0, f"invalid={mov_seq}")

        mov_real = conn.execute(
            text("SELECT count(*) FROM train_movements WHERE classification != 'REAL'")
        ).scalar()
        check("Movements", "All movements classified as REAL", mov_real == 0, f"non_real={mov_real}")

        # 6. Railway Rules Checks
        n_rules = conn.execute(text("SELECT count(*) FROM railway_rules")).scalar()
        check("Rules", "Count is 9", n_rules == 9, f"actual={n_rules}")

        orphan_rule_src = conn.execute(
            text("SELECT count(*) FROM railway_rules r LEFT JOIN source_documents d ON r.source_id = d.source_id WHERE d.source_id IS NULL")
        ).scalar()
        check("Rules", "All source_id FKs valid", orphan_rule_src == 0, f"orphans={orphan_rule_src}")

        rule_class = conn.execute(
            text("SELECT count(*) FROM railway_rules WHERE rule_class != 'VERIFIED_SOURCE'")
        ).scalar()
        check("Rules", "All rules have VERIFIED_SOURCE class", rule_class == 0, f"non_verified={rule_class}")

        # 7. Infrastructure Checks
        n_specs = conn.execute(text("SELECT count(*) FROM infrastructure_specs")).scalar()
        check("Infrastructure", "Specs count is 3", n_specs == 3, f"actual={n_specs}")

        n_corr = conn.execute(text("SELECT count(*) FROM corridors")).scalar()
        check("Infrastructure", "Corridors count is 4", n_corr == 4, f"actual={n_corr}")

        orphan_corr_src = conn.execute(
            text("SELECT count(*) FROM corridors c LEFT JOIN source_documents d ON c.source_id = d.source_id WHERE d.source_id IS NULL")
        ).scalar()
        check("Infrastructure", "Corridor source FKs valid", orphan_corr_src == 0, f"orphans={orphan_corr_src}")

    # Aggregate by Category
    categories = [
        "Source Documents",
        "Stations",
        "Sections",
        "Trains",
        "Movements",
        "Rules",
        "Infrastructure",
    ]

    print("\nTrackMeld Database Validation")
    print("=============================")

    category_results = {}
    for cat in categories:
        cat_checks = [c for c in checks if c[0] == cat]
        all_passed = all(c[2] for c in cat_checks)
        category_results[cat] = all_passed
        status_str = "PASS" if all_passed else "FAIL"
        print(f"{cat:16}: {status_str}")

    foreign_keys_pass = all(
        c[2] for c in checks if "FK" in c[1] or "orphan" in c[1].lower()
    )
    duplicates_pass = all(
        c[2] for c in checks if "duplicate" in c[1].lower()
    )
    provenance_pass = all(
        c[2] for c in checks if "classified" in c[1].lower() or "provenance" in c[1].lower()
    )

    print(f"{'Foreign Keys':16}: {'PASS' if foreign_keys_pass else 'FAIL'}")
    print(f"{'Duplicates':16}: {'PASS' if duplicates_pass else 'FAIL'}")
    print(f"{'Provenance':16}: {'PASS' if provenance_pass else 'FAIL'}")

    n_pass = sum(1 for c in checks if c[2])
    n_fail = sum(1 for c in checks if not c[2])

    print("\nTOTAL:")
    print(f"{n_pass} passed")
    print(f"{n_fail} failed\n")

    if n_fail > 0:
        print("FAILED CHECKS:")
        for c in checks:
            if not c[2]:
                print(f" - [{c[0]}] {c[1]}: {c[3]}")
        return False

    return True


if __name__ == "__main__":
    success = run_checks()
    if not success:
        sys.exit(1)
