#!/usr/bin/env python3
"""Generate Deterministic Synthetic Operational Dataset for TrackMeld Phase 2.

This script synthesizes realistic operational planning entities:
- 1 OperationalScenario (72-hour planning horizon)
- WorkOrders across Engineering, Electrical, S&T departments
- MaintenanceTasks with realistic durations, windows, blocks, buffers, and section locations
- MaintenanceResources (Crews, Track Machines, OHE equipment, S&T gear)
- ResourceAvailability intervals across the horizon
- TaskDependencies forming strict acyclic finish-to-start sequences
- Multi-section spatial impacts and rule references

All generated records are grounded in verified Phase 0 infrastructure (sections, stations, rules)
and explicitly classified as SYNTHETIC with source_id = 'SRC-TRACKMELD-SYNTHETIC-GEN'.

Usage:
    python scripts/generate_synthetic_operational_data.py --seed 20261001 --output data/synthetic/operational_scenario_SCN-DEMO-001.json
"""

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic operational data for TrackMeld.")
    parser.add_argument("--seed", type=int, default=20261001, help="Random seed for deterministic generation.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic/operational_scenario_SCN-DEMO-001.json"),
        help="Target output JSON path.",
    )
    return parser.parse_args()


def load_normalized_data():
    base_dir = Path(__file__).resolve().parent.parent / "data" / "normalized"
    with open(base_dir / "sections.json", "r", encoding="utf-8") as f:
        sections_data = json.load(f)["sections"]
    with open(base_dir / "stations.json", "r", encoding="utf-8") as f:
        stations_data = json.load(f)["stations"]
    with open(base_dir / "rules.json", "r", encoding="utf-8") as f:
        rules_data = json.load(f)["rules"]
    return sections_data, stations_data, rules_data


def generate_dataset(seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    sections_list, stations_list, rules_list = load_normalized_data()

    # Filter to main corridor sections for dense, realistic operations
    corridor_sections = [
        s for s in sections_list
        if any("Delhi - Kanpur" in r or "Delhi - Mumbai" in r or "Delhi - Ambala" in r for r in s.get("routes", []))
    ]
    if len(corridor_sections) < 15:
        corridor_sections = sections_list[:30]

    station_ids = [st["station_id"] for st in stations_list]
    rule_ids = [r["rule_id"] for r in rules_list]

    scenario_start = datetime(2026, 10, 10, 0, 0, 0, tzinfo=timezone.utc)
    scenario_end = scenario_start + timedelta(hours=72)
    scenario_id = "SCN-DEMO-001"

    scenario = {
        "scenario_id": scenario_id,
        "scenario_code": "SCN-DEMO-001",
        "name": "Northern Corridor 72-Hour Integrated Maintenance Scenario",
        "description": "72-hour multi-department rolling block planning scenario across Northern Railway corridor sections.",
        "planning_start": scenario_start.isoformat(),
        "planning_end": scenario_end.isoformat(),
        "generation_seed": seed,
        "dataset_version": "2.0.0",
        "classification": "SYNTHETIC",
        "source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
    }

    # 1. Generate Maintenance Resources (20 resources)
    resources: List[Dict[str, Any]] = [
        # Track Machines
        {"code": "TM-CSM-01", "name": "Continuous Action Tamping Machine CSM-01", "type": "TRACK_MACHINE", "dept": "ENGINEERING", "cap": 1, "station": "STN-GZB", "tags": ["tamping", "plain_track"]},
        {"code": "TM-UNIMAT-02", "name": "Points and Crossing Tamping Machine UNIMAT-02", "type": "TRACK_MACHINE", "dept": "ENGINEERING", "cap": 1, "station": "STN-NDLS", "tags": ["tamping", "turnouts"]},
        {"code": "TM-BCM-03", "name": "Ballast Cleaning Machine BCM-03", "type": "TRACK_MACHINE", "dept": "ENGINEERING", "cap": 1, "station": "STN-ALJN", "tags": ["ballast_cleaning", "deep_screening"]},
        {"code": "TM-DGS-04", "name": "Dynamic Track Stabilizer DGS-04", "type": "TRACK_MACHINE", "dept": "ENGINEERING", "cap": 1, "station": "STN-GZB", "tags": ["stabilizing", "high_speed"]},
        {"code": "TM-RGM-05", "name": "Rail Grinding Machine RGM-05", "type": "TRACK_MACHINE", "dept": "ENGINEERING", "cap": 1, "station": "STN-CNB", "tags": ["rail_grinding", "head_checks"]},
        # OHE Equipment & Tower Wagons
        {"code": "OHE-TW-01", "name": "4-Wheeler OHE Inspection Car TW-01", "type": "OHE_EQUIPMENT", "dept": "ELECTRICAL", "cap": 1, "station": "STN-GZB", "tags": ["ohe_inspection", "cantilever"]},
        {"code": "OHE-TW-02", "name": "8-Wheeler High Power Tower Wagon TW-02", "type": "OHE_EQUIPMENT", "dept": "ELECTRICAL", "cap": 1, "station": "STN-NDLS", "tags": ["ohe_replacement", "contact_wire"]},
        {"code": "OHE-WTR-03", "name": "OHE Wiring Train Unit WTR-03", "type": "OHE_EQUIPMENT", "dept": "ELECTRICAL", "cap": 1, "station": "STN-ALJN", "tags": ["wiring", "catenary"]},
        # S&T Equipment
        {"code": "SNT-AXL-01", "name": "Digital Axle Counter Calibration Unit AXL-01", "type": "S_AND_T_EQUIPMENT", "dept": "S_AND_T", "cap": 1, "station": "STN-NDLS", "tags": ["axle_counter", "testing"]},
        {"code": "SNT-EI-02", "name": "Electronic Interlocking Diagnostic Kit EI-02", "type": "S_AND_T_EQUIPMENT", "dept": "S_AND_T", "cap": 1, "station": "STN-GZB", "tags": ["interlocking", "software_diagnostic"]},
        {"code": "SNT-PMC-03", "name": "Point Machine Overhaul Testing Unit PMC-03", "type": "S_AND_T_EQUIPMENT", "dept": "S_AND_T", "cap": 1, "station": "STN-TDL", "tags": ["points", "overhaul"]},
        # Specialized Vehicles
        {"code": "VEH-CRANE-01", "name": "140-T Breakdown & Bridge Crane CRANE-01", "type": "VEHICLE", "dept": "ENGINEERING", "cap": 1, "station": "STN-NDLS", "tags": ["crane", "bridge_girder"]},
        {"code": "VEH-MAT-02", "name": "Utility Track Material Transport Carrier MAT-02", "type": "VEHICLE", "dept": "ENGINEERING", "cap": 1, "station": "STN-CNB", "tags": ["material_transport", "sleepers"]},
        # Maintenance Gangs / Crews
        {"code": "CREW-ENG-G01", "name": "SSE Permanent Way Track Maintenance Gang 01", "type": "CREW", "dept": "ENGINEERING", "cap": 12, "station": "STN-NDLS", "tags": ["track_maintenance", "welding", "gang"]},
        {"code": "CREW-ENG-G02", "name": "SSE Permanent Way Track Maintenance Gang 02", "type": "CREW", "dept": "ENGINEERING", "cap": 14, "station": "STN-GZB", "tags": ["track_maintenance", "ballast", "gang"]},
        {"code": "CREW-ENG-G03", "name": "SSE Track Machine Support Gang 03", "type": "CREW", "dept": "ENGINEERING", "cap": 8, "station": "STN-ALJN", "tags": ["machine_support", "gang"]},
        {"code": "CREW-ENG-BRG", "name": "Bridge Inspection & Rehabilitation Crew", "type": "CREW", "dept": "ENGINEERING", "cap": 10, "station": "STN-TDL", "tags": ["bridge_work", "bearings"]},
        {"code": "CREW-OHE-G01", "name": "SSE Traction Distribution Lineman Squad 01", "type": "CREW", "dept": "ELECTRICAL", "cap": 6, "station": "STN-NDLS", "tags": ["ohe_maintenance", "isolation"]},
        {"code": "CREW-OHE-G02", "name": "SSE Traction Distribution Lineman Squad 02", "type": "CREW", "dept": "ELECTRICAL", "cap": 6, "station": "STN-GZB", "tags": ["ohe_maintenance", "neutral_section"]},
        {"code": "CREW-SNT-G01", "name": "SSE Signal Maintenance Field Team 01", "type": "CREW", "dept": "S_AND_T", "cap": 5, "station": "STN-NDLS", "tags": ["signal_maintenance", "point_machines"]},
        {"code": "CREW-SNT-G02", "name": "SSE Telecommunication & Optical Fibre Team 02", "type": "CREW", "dept": "S_AND_T", "cap": 4, "station": "STN-ALJN", "tags": ["telecom", "oft_cable"]},
    ]

    resource_records = []
    for r in resources:
        res_id = f"RES-{r['code']}"
        resource_records.append({
            "resource_id": res_id,
            "resource_code": r["code"],
            "name": r["name"],
            "resource_type": r["type"],
            "department": r["dept"],
            "description": f"Dedicated {r['name']} based at {r['station']}",
            "capacity": r["cap"],
            "home_station": r["station"],
            "qualification_tags": r["tags"],
            "classification": "SYNTHETIC",
            "source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
        })

    # 2. Resource Availability (intervals across 72 hours)
    availability_records = []
    avail_idx = 1
    for r in resource_records:
        # Most resources available full 72h
        # 3 resources have maintenance intervals or shifts
        if r["resource_code"] in ("TM-BCM-03", "OHE-TW-02"):
            # Available first 30 hours
            availability_records.append({
                "availability_id": f"AVL-{avail_idx:04d}",
                "resource_id": r["resource_id"],
                "scenario_id": scenario_id,
                "available_from": scenario_start.isoformat(),
                "available_until": (scenario_start + timedelta(hours=30)).isoformat(),
                "availability_status": "AVAILABLE",
                "quantity": r["capacity"],
            })
            avail_idx += 1
            # Maintenance 6 hours
            availability_records.append({
                "availability_id": f"AVL-{avail_idx:04d}",
                "resource_id": r["resource_id"],
                "scenario_id": scenario_id,
                "available_from": (scenario_start + timedelta(hours=30)).isoformat(),
                "available_until": (scenario_start + timedelta(hours=36)).isoformat(),
                "availability_status": "MAINTENANCE",
                "quantity": r["capacity"],
            })
            avail_idx += 1
            # Available remainder 36 hours
            availability_records.append({
                "availability_id": f"AVL-{avail_idx:04d}",
                "resource_id": r["resource_id"],
                "scenario_id": scenario_id,
                "available_from": (scenario_start + timedelta(hours=36)).isoformat(),
                "available_until": scenario_end.isoformat(),
                "availability_status": "AVAILABLE",
                "quantity": r["capacity"],
            })
            avail_idx += 1
        else:
            availability_records.append({
                "availability_id": f"AVL-{avail_idx:04d}",
                "resource_id": r["resource_id"],
                "scenario_id": scenario_id,
                "available_from": scenario_start.isoformat(),
                "available_until": scenario_end.isoformat(),
                "availability_status": "AVAILABLE",
                "quantity": r["capacity"],
            })
            avail_idx += 1

    # 3. Generate Work Orders (12 work orders)
    wo_configs = [
        {"num": "WO-2026-10-001", "dept": "ENGINEERING", "title": "Section Tamping and Ballast Consolidation Package", "unit": "SSE/P-Way/GZB", "by": "Sr.DEN(North)/DLI", "pri": "CRITICAL", "mand": True, "start_h": 4, "end_h": 28},
        {"num": "WO-2026-10-002", "dept": "ENGINEERING", "title": "Turnout Tamping and Switch Overhaul Programme", "unit": "SSE/P-Way/NDLS", "by": "Sr.DEN(Lines)/DLI", "pri": "HIGH", "mand": True, "start_h": 12, "end_h": 36},
        {"num": "WO-2026-10-003", "dept": "ENGINEERING", "title": "Ballast Deep Screening and Shoulder Cleaning", "unit": "SSE/P-Way/ALJN", "by": "Sr.DEN(East)/DLI", "pri": "HIGH", "mand": False, "start_h": 16, "end_h": 48},
        {"num": "WO-2026-10-004", "dept": "ENGINEERING", "title": "Rail Surface Profile Grinding and Defect Remediation", "unit": "SSE/P-Way/CNB", "by": "Sr.DEN(Special)/PRYJ", "pri": "MEDIUM", "mand": False, "start_h": 24, "end_h": 60},
        {"num": "WO-2026-10-005", "dept": "ELECTRICAL", "title": "Periodic OHE Cantilever Inspection & Contact Wire Profiling", "unit": "SSE/TRD/GZB", "by": "Sr.DEE(TRD)/DLI", "pri": "CRITICAL", "mand": True, "start_h": 6, "end_h": 30},
        {"num": "WO-2026-10-006", "dept": "ELECTRICAL", "title": "Neutral Section and Isolator Maintenance", "unit": "SSE/TRD/NDLS", "by": "Sr.DEE(TRD)/DLI", "pri": "HIGH", "mand": True, "start_h": 18, "end_h": 42},
        {"num": "WO-2026-10-007", "dept": "ELECTRICAL", "title": "Catenary Wire Tensioning and Dropper Adjustment", "unit": "SSE/TRD/ALJN", "by": "Sr.DEE(TRD)/PRYJ", "pri": "MEDIUM", "mand": False, "start_h": 36, "end_h": 66},
        {"num": "WO-2026-10-008", "dept": "S_AND_T", "title": "Electronic Interlocking Diagnostic and Relay Test", "unit": "SSE/Signal/NDLS", "by": "Sr.DSTE/DLI", "pri": "HIGH", "mand": True, "start_h": 8, "end_h": 32},
        {"num": "WO-2026-10-009", "dept": "S_AND_T", "title": "Digital Axle Counter Reset & Drift Calibration", "unit": "SSE/Signal/GZB", "by": "Sr.DSTE/DLI", "pri": "CRITICAL", "mand": True, "start_h": 14, "end_h": 38},
        {"num": "WO-2026-10-010", "dept": "S_AND_T", "title": "Point Machine Motor Overhaul and Throw Adjustment", "unit": "SSE/Signal/TDL", "by": "Sr.DSTE/PRYJ", "pri": "HIGH", "mand": False, "start_h": 28, "end_h": 54},
        {"num": "WO-2026-10-011", "dept": "ENGINEERING", "title": "Major Bridge Girder Bearing Inspection and Painting", "unit": "SSE/Bridge/TDL", "by": "Dy.CE(Bridge)/HQ", "pri": "LOW", "mand": False, "start_h": 20, "end_h": 68},
        {"num": "WO-2026-10-012", "dept": "OPERATING", "title": "Joint S&T and Engineering Track Circuit Safety Inspection", "unit": "SSE/Joint/NDLS", "by": "Sr.DOM(General)/DLI", "pri": "MEDIUM", "mand": False, "start_h": 10, "end_h": 50},
    ]

    work_order_records = []
    for idx, wo in enumerate(wo_configs, start=1):
        wo_id = f"WO-{idx:04d}"
        w_start = scenario_start + timedelta(hours=wo["start_h"])
        w_end = scenario_start + timedelta(hours=wo["end_h"])
        work_order_records.append({
            "work_order_id": wo_id,
            "work_order_number": wo["num"],
            "title": wo["title"],
            "department": wo["dept"],
            "requesting_unit": wo["unit"],
            "requested_by": wo["by"],
            "status": "APPROVED",
            "priority": wo["pri"],
            "mandatory": wo["mand"],
            "scenario_id": scenario_id,
            "requested_execution_start": w_start.isoformat(),
            "requested_execution_end": w_end.isoformat(),
            "remarks": f"Authorized under Rolling Block Programme 2026-Q4 ({wo['dept']}).",
            "classification": "SYNTHETIC",
            "source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
        })

    # 4. Generate Maintenance Tasks (32 tasks across work orders)
    task_templates = [
        # Under WO-0001 (Tamping & Stabilizing)
        {"wo_idx": 0, "code": "TSK-TRK-001", "title": "Plain Track CSM Tamping - Up Main Line", "type": "TRACK_MACHINE_WORK", "pri": "CRITICAL", "mand": True, "dur": 180, "tb": True, "pb": False, "ptw": True, "crew": 12, "res_req": [("TRACK_MACHINE", "RES-TM-CSM-01", 1), ("CREW", "RES-CREW-ENG-G01", 1)]},
        {"wo_idx": 0, "code": "TSK-TRK-002", "title": "Dynamic Track Stabilizing Post-Tamping", "type": "TRACK_MACHINE_WORK", "pri": "CRITICAL", "mand": True, "dur": 120, "tb": True, "pb": False, "ptw": True, "crew": 8, "res_req": [("TRACK_MACHINE", "RES-TM-DGS-04", 1), ("CREW", "RES-CREW-ENG-G03", 1)]},
        {"wo_idx": 0, "code": "TSK-TRK-003", "title": "Track Parameter Verification & Dressing", "type": "INSPECTION", "pri": "HIGH", "mand": True, "dur": 90, "tb": False, "pb": False, "ptw": True, "crew": 6, "res_req": [("CREW", "RES-CREW-ENG-G01", 1)]},

        # Under WO-0002 (Turnout Tamping)
        {"wo_idx": 1, "code": "TSK-TRK-004", "title": "Station Yard Turnout UNIMAT Tamping", "type": "TRACK_MACHINE_WORK", "pri": "HIGH", "mand": True, "dur": 150, "tb": True, "pb": False, "ptw": True, "crew": 10, "res_req": [("TRACK_MACHINE", "RES-TM-UNIMAT-02", 1), ("CREW", "RES-CREW-ENG-G02", 1)]},
        {"wo_idx": 1, "code": "TSK-TRK-005", "title": "Switch and Crossings Tongue Rail Replacement", "type": "TRACK_MAINTENANCE", "pri": "HIGH", "mand": True, "dur": 210, "tb": True, "pb": False, "ptw": True, "crew": 14, "res_req": [("CREW", "RES-CREW-ENG-G02", 1)]},

        # Under WO-0003 (Ballast Cleaning)
        {"wo_idx": 2, "code": "TSK-TRK-006", "title": "Deep Ballast Screening by BCM", "type": "TRACK_MACHINE_WORK", "pri": "HIGH", "mand": False, "dur": 240, "tb": True, "pb": False, "ptw": True, "crew": 14, "res_req": [("TRACK_MACHINE", "RES-TM-BCM-03", 1), ("CREW", "RES-CREW-ENG-G02", 1)]},
        {"wo_idx": 2, "code": "TSK-TRK-007", "title": "Track Regrading and Post-Screening Consolidation", "type": "TRACK_MAINTENANCE", "pri": "HIGH", "mand": False, "dur": 120, "tb": True, "pb": False, "ptw": True, "crew": 10, "res_req": [("CREW", "RES-CREW-ENG-G03", 1)]},

        # Under WO-0004 (Rail Grinding)
        {"wo_idx": 3, "code": "TSK-TRK-008", "title": "Continuous High-Speed Rail Grinding", "type": "TRACK_MACHINE_WORK", "pri": "MEDIUM", "mand": False, "dur": 180, "tb": True, "pb": False, "ptw": True, "crew": 8, "res_req": [("TRACK_MACHINE", "RES-TM-RGM-05", 1)]},
        {"wo_idx": 3, "code": "TSK-TRK-009", "title": "Ultrasonic Rail Flaw Post-Grinding Testing", "type": "INSPECTION", "pri": "MEDIUM", "mand": False, "dur": 90, "tb": False, "pb": False, "ptw": True, "crew": 4, "res_req": [("CREW", "RES-CREW-ENG-G03", 1)]},

        # Under WO-0005 (OHE Cantilever & Contact Wire)
        {"wo_idx": 4, "code": "TSK-OHE-010", "title": "OHE Isolation & Power Disconnection", "type": "OHE_MAINTENANCE", "pri": "CRITICAL", "mand": True, "dur": 60, "tb": True, "pb": True, "ptw": True, "crew": 6, "res_req": [("CREW", "RES-CREW-OHE-G01", 1)]},
        {"wo_idx": 4, "code": "TSK-OHE-011", "title": "Cantilever Assembly & Stagger Adjustment", "type": "OHE_MAINTENANCE", "pri": "CRITICAL", "mand": True, "dur": 180, "tb": True, "pb": True, "ptw": True, "crew": 6, "res_req": [("OHE_EQUIPMENT", "RES-OHE-TW-01", 1), ("CREW", "RES-CREW-OHE-G01", 1)]},
        {"wo_idx": 4, "code": "TSK-OHE-012", "title": "OHE Power Restoration and Bonding Test", "type": "OHE_MAINTENANCE", "pri": "CRITICAL", "mand": True, "dur": 45, "tb": True, "pb": True, "ptw": True, "crew": 6, "res_req": [("CREW", "RES-CREW-OHE-G01", 1)]},

        # Under WO-0006 (Neutral Section & Isolator)
        {"wo_idx": 5, "code": "TSK-OHE-013", "title": "Neutral Section Overhaul & Arc Trap Check", "type": "OHE_MAINTENANCE", "pri": "HIGH", "mand": True, "dur": 150, "tb": True, "pb": True, "ptw": True, "crew": 6, "res_req": [("OHE_EQUIPMENT", "RES-OHE-TW-02", 1), ("CREW", "RES-CREW-OHE-G02", 1)]},
        {"wo_idx": 5, "code": "TSK-OHE-014", "title": "Substation Gantry Isolator Contact Cleaning", "type": "OHE_MAINTENANCE", "pri": "HIGH", "mand": True, "dur": 90, "tb": False, "pb": True, "ptw": True, "crew": 4, "res_req": [("CREW", "RES-CREW-OHE-G02", 1)]},

        # Under WO-0007 (Catenary Wire Tensioning)
        {"wo_idx": 6, "code": "TSK-OHE-015", "title": "Auto Tensioning Device (ATD) Weight Balance Check", "type": "OHE_MAINTENANCE", "pri": "MEDIUM", "mand": False, "dur": 120, "tb": False, "pb": True, "ptw": True, "crew": 6, "res_req": [("CREW", "RES-CREW-OHE-G02", 1)]},
        {"wo_idx": 6, "code": "TSK-OHE-016", "title": "Catenary Wire Re-tensioning and Splicing", "type": "OHE_MAINTENANCE", "pri": "MEDIUM", "mand": False, "dur": 180, "tb": True, "pb": True, "ptw": True, "crew": 6, "res_req": [("OHE_EQUIPMENT", "RES-OHE-WTR-03", 1), ("CREW", "RES-CREW-OHE-G01", 1)]},

        # Under WO-0008 (Electronic Interlocking)
        {"wo_idx": 7, "code": "TSK-SIG-017", "title": "EI Diagnostic Software Check & Logic Simulation", "type": "SIGNAL_MAINTENANCE", "pri": "HIGH", "mand": True, "dur": 120, "tb": False, "pb": False, "ptw": True, "crew": 5, "res_req": [("S_AND_T_EQUIPMENT", "RES-SNT-EI-02", 1), ("CREW", "RES-CREW-SNT-G01", 1)]},
        {"wo_idx": 7, "code": "TSK-SIG-018", "title": "Point Detection and Track Circuit Interlocking Test", "type": "SIGNAL_MAINTENANCE", "pri": "HIGH", "mand": True, "dur": 90, "tb": True, "pb": False, "ptw": True, "crew": 5, "res_req": [("CREW", "RES-CREW-SNT-G01", 1)]},

        # Under WO-0009 (Digital Axle Counter)
        {"wo_idx": 8, "code": "TSK-SIG-019", "title": "Axle Counter Track Sensor Alignment & Millivolt Tuning", "type": "SIGNAL_MAINTENANCE", "pri": "CRITICAL", "mand": True, "dur": 90, "tb": True, "pb": False, "ptw": True, "crew": 5, "res_req": [("S_AND_T_EQUIPMENT", "RES-SNT-AXL-01", 1), ("CREW", "RES-CREW-SNT-G01", 1)]},
        {"wo_idx": 8, "code": "TSK-SIG-020", "title": "Evaluator Reset Test & Multi-Section Supervision Check", "type": "SIGNAL_MAINTENANCE", "pri": "CRITICAL", "mand": True, "dur": 60, "tb": True, "pb": False, "ptw": True, "crew": 5, "res_req": [("CREW", "RES-CREW-SNT-G01", 1)]},

        # Under WO-0010 (Point Machine)
        {"wo_idx": 9, "code": "TSK-SIG-021", "title": "Point Machine Motor Current & Throw Time Calibration", "type": "SIGNAL_MAINTENANCE", "pri": "HIGH", "mand": False, "dur": 120, "tb": True, "pb": False, "ptw": True, "crew": 5, "res_req": [("S_AND_T_EQUIPMENT", "RES-SNT-PMC-03", 1), ("CREW", "RES-CREW-SNT-G01", 1)]},
        {"wo_idx": 9, "code": "TSK-SIG-022", "title": "Ground Connection Obstruction Test and Lock Rod Servicing", "type": "SIGNAL_MAINTENANCE", "pri": "HIGH", "mand": False, "dur": 90, "tb": True, "pb": False, "ptw": True, "crew": 5, "res_req": [("CREW", "RES-CREW-SNT-G01", 1)]},

        # Under WO-0011 (Bridge)
        {"wo_idx": 10, "code": "TSK-CVL-023", "title": "Major Bridge Bedblock Inspection and Bearing Cleaning", "type": "BRIDGE_WORK", "pri": "LOW", "mand": False, "dur": 240, "tb": True, "pb": False, "ptw": True, "crew": 10, "res_req": [("CREW", "RES-CREW-ENG-BRG", 1)]},
        {"wo_idx": 10, "code": "TSK-CVL-024", "title": "Girder Rivet Testing & Corrosion Protection Coating", "type": "BRIDGE_WORK", "pri": "LOW", "mand": False, "dur": 180, "tb": False, "pb": False, "ptw": True, "crew": 10, "res_req": [("CREW", "RES-CREW-ENG-BRG", 1)]},

        # Under WO-0012 (Joint Inspection)
        {"wo_idx": 11, "code": "TSK-JNT-025", "title": "Joint Foot Inspection of Glued Insulated Rail Joints", "type": "INSPECTION", "pri": "MEDIUM", "mand": False, "dur": 120, "tb": False, "pb": False, "ptw": True, "crew": 6, "res_req": [("CREW", "RES-CREW-ENG-G01", 1), ("CREW", "RES-CREW-SNT-G01", 1)]},
        {"wo_idx": 11, "code": "TSK-JNT-026", "title": "Track Circuit Feed Point & Bonding Integrity Verification", "type": "INSPECTION", "pri": "MEDIUM", "mand": False, "dur": 90, "tb": False, "pb": False, "ptw": True, "crew": 6, "res_req": [("CREW", "RES-CREW-SNT-G01", 1)]},

        # Extra operational tasks for solver pressure (high density)
        {"wo_idx": 0, "code": "TSK-TRK-027", "title": "Post-Stabilizing Flash Butt Weld Ultrasonic Testing", "type": "INSPECTION", "pri": "HIGH", "mand": True, "dur": 90, "tb": False, "pb": False, "ptw": True, "crew": 6, "res_req": [("CREW", "RES-CREW-ENG-G01", 1)]},
        {"wo_idx": 4, "code": "TSK-OHE-028", "title": "Section Insulator Sparking Erosion Measurement", "type": "OHE_MAINTENANCE", "pri": "HIGH", "mand": True, "dur": 75, "tb": True, "pb": True, "ptw": True, "crew": 6, "res_req": [("OHE_EQUIPMENT", "RES-OHE-TW-01", 1), ("CREW", "RES-CREW-OHE-G01", 1)]},
        {"wo_idx": 8, "code": "TSK-SIG-029", "title": "Axle Counter Wheel Detection Channel A/B Voltage Log", "type": "SIGNAL_MAINTENANCE", "pri": "HIGH", "mand": True, "dur": 60, "tb": False, "pb": False, "ptw": True, "crew": 4, "res_req": [("CREW", "RES-CREW-SNT-G01", 1)]},
        {"wo_idx": 1, "code": "TSK-TRK-030", "title": "Turnout Check Rail Clearance & Flangeway Tuning", "type": "TRACK_MAINTENANCE", "pri": "MEDIUM", "mand": False, "dur": 105, "tb": True, "pb": False, "ptw": True, "crew": 8, "res_req": [("CREW", "RES-CREW-ENG-G02", 1)]},
    ]

    task_records = []
    task_req_records = []
    task_section_links = []
    task_rule_links = []
    req_idx = 1

    for idx, t in enumerate(task_templates, start=1):
        task_id = f"TSK-{idx:04d}"
        wo = work_order_records[t["wo_idx"]]

        # Select a primary section from corridor sections deterministically
        sec = corridor_sections[(idx * 7) % len(corridor_sections)]
        sec_id = sec["section_id"]
        corridor_id = "CORR-NDLS-HWH"

        # Timing: window within work order window
        wo_start = datetime.fromisoformat(wo["requested_execution_start"])
        wo_end = datetime.fromisoformat(wo["requested_execution_end"])
        
        # Sub-window
        window_duration_hours = max(4, int((wo_end - wo_start).total_seconds() / 3600))
        offset_hours = (idx * 3) % (window_duration_hours - 2)
        task_w_start = wo_start + timedelta(hours=offset_hours)
        task_w_end = min(wo_end, task_w_start + timedelta(hours=max(3, t["dur"] // 60 + 2)))

        # Preferred start inside window
        pref_start = task_w_start + timedelta(minutes=15)
        pref_end = pref_start + timedelta(minutes=t["dur"])

        task_records.append({
            "task_id": task_id,
            "work_order_id": wo["work_order_id"],
            "task_code": t["code"],
            "title": t["title"],
            "description": f"{t['title']} on block section {sec_id}.",
            "task_type": t["type"],
            "status": "PLANNED",
            "priority": t["pri"],
            "mandatory": t["mand"],
            "section_id": sec_id,
            "station_id": sec.get("from_station_id"),
            "corridor_id": corridor_id,
            "scenario_id": scenario_id,
            "window_start": task_w_start.isoformat(),
            "window_end": task_w_end.isoformat(),
            "preferred_start": pref_start.isoformat(),
            "preferred_end": pref_end.isoformat(),
            "estimated_duration_minutes": t["dur"],
            "minimum_duration_minutes": max(30, t["dur"] - 30),
            "maximum_duration_minutes": t["dur"] + 30,
            "requires_traffic_block": t["tb"],
            "requires_power_block": t["pb"],
            "requires_ptw": t["ptw"],
            "requires_ohe_isolation": t["pb"],
            "requires_signal_disconnection": (t["type"] == "SIGNAL_MAINTENANCE"),
            "safety_buffer_before_minutes": 15,
            "safety_buffer_after_minutes": 15,
            "crew_size_required": t["crew"],
            "classification": "SYNTHETIC",
            "source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
        })

        # Add resource requirements
        for r_type, r_id, q in t["res_req"]:
            task_req_records.append({
                "requirement_id": f"REQ-{req_idx:04d}",
                "task_id": task_id,
                "resource_id": r_id,
                "resource_type": r_type,
                "quantity": q,
                "mandatory": True,
            })
            req_idx += 1

        # Link rule references
        # Every traffic block requires RULE-OPER-GR-1506
        if t["tb"] and "RULE-OPER-GR-1506" in rule_ids:
            task_rule_links.append({"task_id": task_id, "rule_id": "RULE-OPER-GR-1506"})
        if t["pb"] and "RULE-ELEC-OHE-1510" in rule_ids:
            task_rule_links.append({"task_id": task_id, "rule_id": "RULE-ELEC-OHE-1510"})
        if t["type"] == "SIGNAL_MAINTENANCE" and "RULE-SIG-DISC-1511" in rule_ids:
            task_rule_links.append({"task_id": task_id, "rule_id": "RULE-SIG-DISC-1511"})
        if t["mand"] and "RULE-STAT-RBP-1502C" in rule_ids:
            task_rule_links.append({"task_id": task_id, "rule_id": "RULE-STAT-RBP-1502C"})

        # Multi-section spatial impact for 3 specific machine/bridge tasks
        if t["code"] in ("TSK-TRK-006", "TSK-CVL-023", "TSK-TRK-008"):
            # pick adjacent section
            adj_sec = corridor_sections[((idx * 7) + 1) % len(corridor_sections)]
            if adj_sec["section_id"] != sec_id:
                task_section_links.append({"task_id": task_id, "section_id": adj_sec["section_id"]})

    # 5. Generate Task Dependencies (strict finish-to-start sequences)
    # TSK-0001 (Tamping) -> TSK-0002 (Stabilizing)
    # TSK-0002 (Stabilizing) -> TSK-0003 (Verification)
    # TSK-0004 (Turnout Tamping) -> TSK-0005 (Tongue Rail Replacement)
    # TSK-0006 (Deep Screening) -> TSK-0007 (Consolidation)
    # TSK-0008 (Rail Grinding) -> TSK-0009 (Ultrasonic Testing)
    # TSK-0010 (OHE Isolation) -> TSK-0011 (Cantilever Adjustment)
    # TSK-0011 (Cantilever Adjustment) -> TSK-0012 (Power Restoration)
    # TSK-0017 (EI Diagnostic) -> TSK-0018 (Interlocking Test)
    # TSK-0019 (Axle Sensor Alignment) -> TSK-0020 (Evaluator Reset)
    # TSK-0021 (Point Motor) -> TSK-0022 (Obstruction Test)
    # TSK-0023 (Bridge Bedblock) -> TSK-0024 (Girder Coating)

    dep_pairs = [
        ("TSK-0001", "TSK-0002"),
        ("TSK-0002", "TSK-0003"),
        ("TSK-0004", "TSK-0005"),
        ("TSK-0006", "TSK-0007"),
        ("TSK-0008", "TSK-0009"),
        ("TSK-0010", "TSK-0011"),
        ("TSK-0011", "TSK-0012"),
        ("TSK-0017", "TSK-0018"),
        ("TSK-0019", "TSK-0020"),
        ("TSK-0021", "TSK-0022"),
        ("TSK-0023", "TSK-0024"),
    ]

    dependency_records = []
    for d_idx, (p_id, s_id) in enumerate(dep_pairs, start=1):
        dependency_records.append({
            "dependency_id": f"DEP-{d_idx:04d}",
            "predecessor_task_id": p_id,
            "successor_task_id": s_id,
            "dependency_type": "FINISH_TO_START",
        })

    dataset = {
        "metadata": {
            "dataset_name": "TrackMeld Synthetic Operational Scenario Dataset",
            "scenario_code": "SCN-DEMO-001",
            "generation_seed": seed,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator_version": "2.0.0",
            "classification": "SYNTHETIC",
            "provenance_source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
            "description": "Deterministic synthetic operational scenario grounded in Phase 0 railway reference data.",
        },
        "scenario": scenario,
        "resources": resource_records,
        "resource_availabilities": availability_records,
        "work_orders": work_order_records,
        "maintenance_tasks": task_records,
        "task_resource_requirements": task_req_records,
        "task_dependencies": dependency_records,
        "task_additional_sections": task_section_links,
        "task_rule_references": task_rule_links,
    }

    return dataset


def main():
    args = parse_args()
    print(f"Generating synthetic operational dataset with seed={args.seed}...")
    dataset = generate_dataset(args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    counts = {
        "scenario": 1,
        "resources": len(dataset["resources"]),
        "availabilities": len(dataset["resource_availabilities"]),
        "work_orders": len(dataset["work_orders"]),
        "tasks": len(dataset["maintenance_tasks"]),
        "resource_requirements": len(dataset["task_resource_requirements"]),
        "dependencies": len(dataset["task_dependencies"]),
        "additional_sections": len(dataset["task_additional_sections"]),
        "rule_references": len(dataset["task_rule_references"]),
    }
    print(f"Dataset generated successfully at: {args.output}")
    print("Entity counts:")
    for k, v in counts.items():
        print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
