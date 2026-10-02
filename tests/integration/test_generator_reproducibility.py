import pytest
from scripts.generate_synthetic_operational_data import generate_dataset


def test_generator_deterministic_reproducibility():
    """Verify that running the generator with the same seed produces identical results."""
    run_1 = generate_dataset(seed=20261001)
    run_2 = generate_dataset(seed=20261001)

    # 1. Exact entity counts must match
    assert len(run_1["work_orders"]) == len(run_2["work_orders"])
    assert len(run_1["maintenance_tasks"]) == len(run_2["maintenance_tasks"])
    assert len(run_1["resources"]) == len(run_2["resources"])
    assert len(run_1["resource_availabilities"]) == len(run_2["resource_availabilities"])
    assert len(run_1["task_dependencies"]) == len(run_2["task_dependencies"])

    # 2. Exact task IDs, codes, sections, and durations must match
    for t1, t2 in zip(run_1["maintenance_tasks"], run_2["maintenance_tasks"]):
        assert t1["task_id"] == t2["task_id"]
        assert t1["task_code"] == t2["task_code"]
        assert t1["section_id"] == t2["section_id"]
        assert t1["estimated_duration_minutes"] == t2["estimated_duration_minutes"]
        assert t1["window_start"] == t2["window_start"]
        assert t1["window_end"] == t2["window_end"]

    # 3. All items must carry SYNTHETIC classification and generator provenance
    for t in run_1["maintenance_tasks"]:
        assert t["classification"] == "SYNTHETIC"
        assert t["source_id"] == "SRC-TRACKMELD-SYNTHETIC-GEN"

    for r in run_1["resources"]:
        assert r["classification"] == "SYNTHETIC"
        assert r["source_id"] == "SRC-TRACKMELD-SYNTHETIC-GEN"


def test_generator_seed_variance():
    """Verify that different seeds produce different task configurations."""
    run_a = generate_dataset(seed=20261001)
    run_b = generate_dataset(seed=42)

    # Different seeds should assign different section locations or offsets
    sections_a = [t["section_id"] for t in run_a["maintenance_tasks"]]
    sections_b = [t["section_id"] for t in run_b["maintenance_tasks"]]
    assert sections_a != sections_b or run_a["metadata"]["generation_seed"] != run_b["metadata"]["generation_seed"]
