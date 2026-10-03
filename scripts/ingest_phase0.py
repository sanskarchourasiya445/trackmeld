"""
TrackMeld Phase 1 — Deterministic Reference Data Ingestion Script.

Reads Phase 0 normalized datasets, validates against Pydantic domain models,
and loads them idempotently into PostgreSQL.
"""

import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from backend.app.config import get_settings
from backend.app.db.session import sync_engine
from backend.app.domain import (
    SourceDocument,
    Station,
    Section,
    Train,
    TrainMovement,
    RailwayRule,
    InfrastructureSpec,
    Corridor,
    DataClass,
)
from backend.app.db.models import (
    SourceDocumentModel,
    StationModel,
    SectionModel,
    TrainModel,
    TrainMovementModel,
    RailwayRuleModel,
    InfrastructureSpecModel,
    CorridorModel,
    TrackModel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_phase0")

DATA_DIR = BASE_DIR / "data"


def load_json(rel_path: str) -> dict:
    full_path = DATA_DIR / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"Required Phase 0 data file not found: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_sources(session) -> int:
    logger.info("Ingesting Source Documents...")
    raw = load_json("metadata/sources.json")
    sources = [SourceDocument.model_validate(s) for s in raw["sources"]]
    count = 0
    for s in sources:
        stmt = insert(SourceDocumentModel).values(
            source_id=s.source_id,
            title=s.title,
            publisher=s.publisher,
            organization=s.organization,
            source_class=s.source_class,
            source_url=s.source_url,
            local_path=s.local_path,
            file_size_bytes=s.file_size_bytes,
            document_date=s.document_date,
            version=s.version,
            downloaded_at=s.downloaded_at,
            sha256=s.sha256,
            data_types=s.data_types,
            authority_level=s.authority_level,
            notes=s.notes,
        ).on_conflict_do_update(
            index_elements=[SourceDocumentModel.source_id],
            set_={
                "title": s.title,
                "publisher": s.publisher,
                "organization": s.organization,
                "source_class": s.source_class,
                "source_url": s.source_url,
                "local_path": s.local_path,
                "file_size_bytes": s.file_size_bytes,
                "document_date": s.document_date,
                "version": s.version,
                "downloaded_at": s.downloaded_at,
                "sha256": s.sha256,
                "data_types": s.data_types,
                "authority_level": s.authority_level,
                "notes": s.notes,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_stations(session) -> int:
    logger.info("Ingesting Stations...")
    raw = load_json("normalized/stations.json")
    stations = [Station.model_validate(s) for s in raw["stations"]]
    count = 0
    for s in stations:
        stmt = insert(StationModel).values(
            station_id=s.station_id,
            station_code=s.station_code,
            station_name=s.station_name,
            zone=s.zone,
            division=s.division,
            route=s.route,
            route_km=s.route_km,
            station_type=s.station_type,
            classification=s.classification,
            source_id=s.source_id,
            source_reference=s.source_reference,
        ).on_conflict_do_update(
            index_elements=[StationModel.station_id],
            set_={
                "station_code": s.station_code,
                "station_name": s.station_name,
                "zone": s.zone,
                "division": s.division,
                "route": s.route,
                "route_km": s.route_km,
                "station_type": s.station_type,
                "classification": s.classification,
                "source_id": s.source_id,
                "source_reference": s.source_reference,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_sections(session) -> int:
    logger.info("Ingesting Block Sections...")
    raw = load_json("normalized/sections.json")
    sections = [Section.model_validate(s) for s in raw["sections"]]
    count = 0
    for s in sections:
        stmt = insert(SectionModel).values(
            section_id=s.section_id,
            section_code=s.section_code,
            from_station_id=s.from_station_id,
            to_station_id=s.to_station_id,
            from_station_name=s.from_station_name,
            to_station_name=s.to_station_name,
            from_station_code=s.from_station_code,
            to_station_code=s.to_station_code,
            routes=s.routes,
            division=s.division,
            zone=s.zone,
            kilometrage_start=s.kilometrage_start,
            kilometrage_end=s.kilometrage_end,
            length_km=s.length_km,
            track_count=s.track_count,
            electrified=s.electrified,
            gauge=s.gauge,
            signalling_type=s.signalling_type,
            classification=s.classification,
            derivation_method=s.derivation_method,
            input_source_ids=s.input_source_ids,
            confidence=s.confidence,
        ).on_conflict_do_update(
            index_elements=[SectionModel.section_id],
            set_={
                "section_code": s.section_code,
                "from_station_id": s.from_station_id,
                "to_station_id": s.to_station_id,
                "from_station_name": s.from_station_name,
                "to_station_name": s.to_station_name,
                "from_station_code": s.from_station_code,
                "to_station_code": s.to_station_code,
                "routes": s.routes,
                "division": s.division,
                "zone": s.zone,
                "kilometrage_start": s.kilometrage_start,
                "kilometrage_end": s.kilometrage_end,
                "length_km": s.length_km,
                "track_count": s.track_count,
                "electrified": s.electrified,
                "gauge": s.gauge,
                "signalling_type": s.signalling_type,
                "classification": s.classification,
                "derivation_method": s.derivation_method,
                "input_source_ids": s.input_source_ids,
                "confidence": s.confidence,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_trains(session) -> int:
    logger.info("Ingesting Trains...")
    raw = load_json("normalized/trains.json")
    trains = [Train.model_validate(t) for t in raw["trains"]]
    count = 0
    # Batch execute in chunks of 500
    batch_size = 500
    for i in range(0, len(trains), batch_size):
        chunk = trains[i : i + batch_size]
        for t in chunk:
            stmt = insert(TrainModel).values(
                train_id=t.train_id,
                train_number=t.train_number,
                train_name=t.train_name,
                train_type=t.train_type,
                source_station=t.source_station,
                destination_station=t.destination_station,
                corridor_table=t.corridor_table,
                running_days=t.running_days,
                classification=t.classification,
                source_id=t.source_id,
                source_reference=t.source_reference,
            ).on_conflict_do_update(
                index_elements=[TrainModel.train_id],
                set_={
                    "train_number": t.train_number,
                    "train_name": t.train_name,
                    "train_type": t.train_type,
                    "source_station": t.source_station,
                    "destination_station": t.destination_station,
                    "corridor_table": t.corridor_table,
                    "running_days": t.running_days,
                    "classification": t.classification,
                    "source_id": t.source_id,
                    "source_reference": t.source_reference,
                },
            )
            session.execute(stmt)
            count += 1
    return count


def ingest_movements(session) -> int:
    logger.info("Ingesting Train Movements...")
    raw = load_json("normalized/train_movements.json")
    movements = [TrainMovement.model_validate(m) for m in raw["movements"]]
    count = 0
    for m in movements:
        stmt = insert(TrainMovementModel).values(
            movement_id=m.movement_id,
            train_id=m.train_id,
            train_number=m.train_number,
            train_name=m.train_name,
            station_id=m.station_id,
            station_code=m.station_code,
            station_name=m.station_name,
            stop_sequence=m.stop_sequence,
            scheduled_arrival=m.scheduled_arrival,
            scheduled_departure=m.scheduled_departure,
            day_offset=m.day_offset,
            distance_km=m.distance_km,
            movement_type=m.movement_type,
            basis=m.basis,
            classification=m.classification,
            source_id=m.source_id,
            source_reference=m.source_reference,
        ).on_conflict_do_update(
            index_elements=[TrainMovementModel.movement_id],
            set_={
                "train_id": m.train_id,
                "train_number": m.train_number,
                "train_name": m.train_name,
                "station_id": m.station_id,
                "station_code": m.station_code,
                "station_name": m.station_name,
                "stop_sequence": m.stop_sequence,
                "scheduled_arrival": m.scheduled_arrival,
                "scheduled_departure": m.scheduled_departure,
                "day_offset": m.day_offset,
                "distance_km": m.distance_km,
                "movement_type": m.movement_type,
                "basis": m.basis,
                "classification": m.classification,
                "source_id": m.source_id,
                "source_reference": m.source_reference,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_rules(session) -> int:
    logger.info("Ingesting Railway Rules...")
    raw = load_json("normalized/rules.json")
    rules = [RailwayRule.model_validate(r) for r in raw["rules"]]
    count = 0
    for r in rules:
        stmt = insert(RailwayRuleModel).values(
            rule_id=r.rule_id,
            category=r.category,
            title=r.title,
            source_document=r.source_document,
            source_id=r.source_id,
            section_page=r.section_page,
            original_text=r.original_text,
            normalized_summary=r.normalized_summary,
            applicability=r.applicability,
            safety_critical=r.safety_critical,
            rule_class=r.rule_class,
            confidence=r.confidence,
        ).on_conflict_do_update(
            index_elements=[RailwayRuleModel.rule_id],
            set_={
                "category": r.category,
                "title": r.title,
                "source_document": r.source_document,
                "source_id": r.source_id,
                "section_page": r.section_page,
                "original_text": r.original_text,
                "normalized_summary": r.normalized_summary,
                "applicability": r.applicability,
                "safety_critical": r.safety_critical,
                "rule_class": r.rule_class,
                "confidence": r.confidence,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_infrastructure(session) -> int:
    logger.info("Ingesting Infrastructure Specifications and Corridors...")
    raw = load_json("normalized/infrastructure.json")
    count = 0

    # 1. Specs
    specs = [
        ("SPEC-ELECTRIFICATION-SYSTEM", "ELECTRIFICATION", "system", raw["electrification"]["system"], raw["electrification"]),
        ("SPEC-TRACK-GAUGE", "TRACK_GAUGE", "gauge_type", str(raw["track_gauge"]["dimension_mm"]) + "mm", raw["track_gauge"]),
        ("SPEC-SIGNALLING-INTERLOCKING", "SIGNALLING", "type", raw["signalling_and_interlocking"]["type"], raw["signalling_and_interlocking"]),
    ]
    for spec_id, category, key, val, details in specs:
        stmt = insert(InfrastructureSpecModel).values(
            spec_id=spec_id,
            category=category,
            spec_key=key,
            spec_value=val,
            attributes=details,
            classification=DataClass.REAL,
            source_id=details.get("source_id", "SRC-MOR-IRWM-2026"),
        ).on_conflict_do_update(
            index_elements=[InfrastructureSpecModel.spec_id],
            set_={
                "category": category,
                "spec_key": key,
                "spec_value": val,
                "attributes": details,
                "classification": DataClass.REAL,
                "source_id": details.get("source_id", "SRC-MOR-IRWM-2026"),
            },
        )
        session.execute(stmt)
        count += 1

    # 2. Corridors
    for corr in raw.get("monitored_corridors", []):
        c = Corridor.model_validate(corr)
        stmt = insert(CorridorModel).values(
            corridor_id=c.corridor_id,
            name=c.name,
            length_km=c.length_km,
            zones=c.zones,
            divisions=c.divisions,
            primary_table=c.primary_table,
            classification=c.classification,
            source_id=c.source_id,
        ).on_conflict_do_update(
            index_elements=[CorridorModel.corridor_id],
            set_={
                "name": c.name,
                "length_km": c.length_km,
                "zones": c.zones,
                "divisions": c.divisions,
                "primary_table": c.primary_table,
                "classification": c.classification,
                "source_id": c.source_id,
            },
        )
        session.execute(stmt)
        count += 1

    return count


def ingest_tracks(session) -> int:
    logger.info("Ingesting Default Tracks for Sections...")
    sections = session.execute(
        select(
            SectionModel.section_id,
            SectionModel.section_code,
            SectionModel.track_count,
            SectionModel.electrified,
        )
    ).all()
    count = 0
    for sec_id, sec_code, trk_cnt, electrified in sections:
        if trk_cnt and trk_cnt >= 2:
            tracks_data = [
                (f"TRK-{sec_code}-UP", "UP_MAIN", "UP", bool(electrified), 130),
                (f"TRK-{sec_code}-DN", "DN_MAIN", "DOWN", bool(electrified), 130),
            ]
        else:
            tracks_data = [
                (f"TRK-{sec_code}-SL", "SINGLE_LINE", "BIDIRECTIONAL", bool(electrified), 100),
            ]
        for trk_id, trk_code, direction, is_elec, max_spd in tracks_data:
            stmt = insert(TrackModel).values(
                track_id=trk_id,
                section_id=sec_id,
                track_code=trk_code,
                direction=direction,
                electrified=is_elec,
                max_speed_kmh=max_spd,
            ).on_conflict_do_update(
                index_elements=[TrackModel.track_id],
                set_={
                    "section_id": sec_id,
                    "track_code": trk_code,
                    "direction": direction,
                    "electrified": is_elec,
                    "max_speed_kmh": max_spd,
                },
            )
            session.execute(stmt)
            count += 1
    return count


def run_ingestion():
    start_time = time.perf_counter()
    logger.info("Beginning Deterministic Ingestion of Phase 0 Data Foundation...")

    from sqlalchemy.orm import Session
    with Session(sync_engine) as session:
        with session.begin():
            n_sources = ingest_sources(session)
            n_stations = ingest_stations(session)
            n_sections = ingest_sections(session)
            n_tracks = ingest_tracks(session)
            n_trains = ingest_trains(session)
            n_movements = ingest_movements(session)
            n_rules = ingest_rules(session)
            n_infra = ingest_infrastructure(session)

    elapsed = time.perf_counter() - start_time
    logger.info("=" * 60)
    logger.info("PHASE 0 INGESTION COMPLETED IN %.2f SECONDS", elapsed)
    logger.info("Source Documents:   %d", n_sources)
    logger.info("Stations:           %d", n_stations)
    logger.info("Block Sections:     %d", n_sections)
    logger.info("Tracks:             %d", n_tracks)
    logger.info("Trains:             %d", n_trains)
    logger.info("Train Movements:    %d", n_movements)
    logger.info("Railway Rules:      %d", n_rules)
    logger.info("Infrastructure:     %d (specs + corridors)", n_infra)
    logger.info("Total Records:      %d", n_sources + n_stations + n_sections + n_tracks + n_trains + n_movements + n_rules + n_infra)
    logger.info("=" * 60)


if __name__ == "__main__":
    run_ingestion()
