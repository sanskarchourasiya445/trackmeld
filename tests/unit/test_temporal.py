import pytest
from datetime import datetime, timezone, timedelta
from backend.app.domain.temporal import TimeInterval, PlanningHorizon


def test_time_interval_valid_creation():
    t1 = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    interval = TimeInterval(start=t1, end=t2)
    assert interval.is_valid
    assert interval.duration_minutes == 120.0
    assert interval.duration_hours == 2.0


def test_time_interval_zero_duration():
    t1 = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    interval = TimeInterval(start=t1, end=t1)
    assert not interval.is_valid
    assert interval.duration_seconds == 0.0


def test_time_interval_negative_duration():
    t1 = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    interval = TimeInterval(start=t1, end=t2)
    assert not interval.is_valid
    assert interval.duration_seconds < 0


def test_half_open_overlapping_intervals():
    # [10:00, 12:00) and [11:00, 13:00) overlap between 11:00 and 12:00
    i1 = TimeInterval(
        start=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
    )
    i2 = TimeInterval(
        start=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 13, 0, tzinfo=timezone.utc),
    )
    assert i1.overlaps(i2)
    assert i2.overlaps(i1)
    inter = i1.intersection(i2)
    assert inter is not None
    assert inter.start == datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc)
    assert inter.end == datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def test_half_open_adjacent_intervals_do_not_overlap():
    # [10:00, 11:00) and [11:00, 12:00) meet at 11:00 and DO NOT overlap
    i1 = TimeInterval(
        start=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc),
    )
    i2 = TimeInterval(
        start=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
    )
    assert not i1.overlaps(i2)
    assert not i2.overlaps(i1)
    assert i1.is_adjacent_to(i2)
    assert i2.is_adjacent_to(i1)
    assert i1.intersection(i2) is None


def test_half_open_exact_boundary_equality():
    i1 = TimeInterval(
        start=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
    )
    i2 = TimeInterval(
        start=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
    )
    assert i1.overlaps(i2)
    assert i1.contains_interval(i2)
    assert not i1.is_adjacent_to(i2)


def test_half_open_point_containment():
    i = TimeInterval(
        start=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
    )
    # Start point is INCLUDED [start
    assert i.contains_point(datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc))
    # Intermediate point is INCLUDED
    assert i.contains_point(datetime(2026, 10, 10, 11, 30, tzinfo=timezone.utc))
    # End point is EXCLUDED end)
    assert not i.contains_point(datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc))
    # Point after is EXCLUDED
    assert not i.contains_point(datetime(2026, 10, 10, 12, 1, tzinfo=timezone.utc))


def test_planning_horizon():
    h_start = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    h_end = h_start + timedelta(hours=72)
    horizon = PlanningHorizon(start=h_start, end=h_end)
    assert horizon.duration_hours == 72.0

    # Inside
    valid_int = TimeInterval(start=h_start + timedelta(hours=2), end=h_start + timedelta(hours=6))
    assert horizon.contains_interval(valid_int)

    # Starts before horizon
    bad_start_int = TimeInterval(start=h_start - timedelta(minutes=1), end=h_start + timedelta(hours=2))
    assert not horizon.contains_interval(bad_start_int)

    # Ends after horizon
    bad_end_int = TimeInterval(start=h_end - timedelta(hours=1), end=h_end + timedelta(minutes=5))
    assert not horizon.contains_interval(bad_end_int)
