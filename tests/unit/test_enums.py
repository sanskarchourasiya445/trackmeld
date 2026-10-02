from backend.app.domain.enums import (
    DataClass,
    BlockType,
    WorkDepartment,
    TaskStatus,
    StationType,
    MovementType,
    MovementBasis,
    RuleClass,
    SourceClass,
)


def test_data_class_values():
    assert set(DataClass) == {
        DataClass.REAL,
        DataClass.DERIVED,
        DataClass.SYNTHETIC,
        DataClass.ASSUMED,
    }


def test_block_type_values():
    assert set(BlockType) == {
        BlockType.TRAFFIC,
        BlockType.POWER,
        BlockType.TRAFFIC_AND_POWER,
    }


def test_work_department_values():
    assert WorkDepartment.ENGINEERING == "ENGINEERING"
    assert WorkDepartment.ELECTRICAL == "ELECTRICAL"
    assert WorkDepartment.S_AND_T == "S_AND_T"
    assert WorkDepartment.OPERATING == "OPERATING"


def test_rule_class_values():
    assert RuleClass.VERIFIED_SOURCE == "VERIFIED_SOURCE"
    assert RuleClass.ASSUMPTION == "ASSUMPTION"
    assert RuleClass.DEMO_ONLY == "DEMO_ONLY"
