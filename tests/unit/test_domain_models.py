import pytest
from pydantic import ValidationError
from backend.app.domain import (
    Station,
    Section,
    Train,
    TrainMovement,
    RailwayRule,
    DataClass,
    RuleClass,
)


def test_station_domain_model():
    stn = Station(
        station_id="STN-NDLS",
        station_code="NDLS",
        station_name="New Delhi",
        zone="NR",
        division="Delhi",
        route="Northern Trunk",
        route_km=0.0,
        station_type="MAJOR_TERMINAL",
        classification=DataClass.REAL,
        source_id="SRC-TAG-2023-TBL-01",
    )
    assert stn.station_code == "NDLS"
    assert stn.classification == DataClass.REAL


def test_section_domain_model_valid():
    sec = Section(
        section_id="SEC-NDLS-GZB",
        section_code="NDLS-GZB",
        from_station_id="STN-NDLS",
        to_station_id="STN-GZB",
        from_station_name="New Delhi",
        to_station_name="Ghaziabad",
        from_station_code="NDLS",
        to_station_code="GZB",
        routes=["Delhi - Kanpur - Howrah Mainline"],
        division="Delhi",
        zone="NR",
        kilometrage_start=0.0,
        kilometrage_end=25.0,
        length_km=25.0,
        classification=DataClass.DERIVED,
        derivation_method="Topological connection",
        input_source_ids=["SRC-TAG-2023-TBL-01"],
    )
    assert sec.length_km == 25.0
    assert sec.classification == DataClass.DERIVED


def test_section_identical_endpoints_rejected():
    with pytest.raises(ValidationError, match="Section endpoint stations cannot be identical"):
        Section(
            section_id="SEC-NDLS-NDLS",
            section_code="NDLS-NDLS",
            from_station_id="STN-NDLS",
            to_station_id="STN-NDLS",
            from_station_name="New Delhi",
            to_station_name="New Delhi",
            from_station_code="NDLS",
            to_station_code="NDLS",
            division="Delhi",
            zone="NR",
            kilometrage_start=0.0,
            kilometrage_end=25.0,
            length_km=25.0,
        )


def test_section_non_positive_length_rejected():
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        Section(
            section_id="SEC-NDLS-GZB",
            section_code="NDLS-GZB",
            from_station_id="STN-NDLS",
            to_station_id="STN-GZB",
            from_station_name="New Delhi",
            to_station_name="Ghaziabad",
            from_station_code="NDLS",
            to_station_code="GZB",
            division="Delhi",
            zone="NR",
            kilometrage_start=25.0,
            kilometrage_end=25.0,
            length_km=0.0,
        )


def test_train_movement_time_format():
    mov = TrainMovement(
        movement_id="MOV-12301-HWH-01",
        train_id="TRN-12301",
        train_number="12301",
        train_name="Howrah Rajdhani",
        station_id="STN-HWH",
        station_code="HWH",
        station_name="Howrah",
        stop_sequence=1,
        scheduled_arrival=None,
        scheduled_departure="16:50",
        movement_type="SCHEDULED_ORIGIN",
        source_id="SRC-TAG-2023-TBL-01",
    )
    assert mov.scheduled_departure == "16:50"

    with pytest.raises(ValueError, match="must be in 24-hour HH:MM format"):
        TrainMovement(
            movement_id="MOV-12301-HWH-01",
            train_id="TRN-12301",
            train_number="12301",
            train_name="Howrah Rajdhani",
            station_id="STN-HWH",
            station_code="HWH",
            station_name="Howrah",
            stop_sequence=1,
            scheduled_departure="25:99",
            movement_type="SCHEDULED_ORIGIN",
            source_id="SRC-TAG-2023-TBL-01",
        )


def test_railway_rule_domain_model():
    rule = RailwayRule(
        rule_id="RULE-STAT-RBP-1502C",
        category="MAINTENANCE_PLANNING",
        title="Mandatory Planning under Rolling Block Programme",
        source_document="Gazette of India G.S.R. 870(E)",
        source_id="SRC-GOI-GSR-870E-2023",
        original_text="Planned maintenance shall be executed in accordance with Rolling Block Programme...",
        normalized_summary="52-week rolling window updated weekly.",
        applicability="ALL_ZONES_DIVISIONS",
        safety_critical=True,
        rule_class=RuleClass.VERIFIED_SOURCE,
    )
    assert rule.safety_critical is True
    assert rule.rule_class == RuleClass.VERIFIED_SOURCE
