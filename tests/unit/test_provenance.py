import pytest
from backend.app.domain.enums import DataClass
from backend.app.domain.provenance import (
    ProvenanceMetadata,
    assert_classification_immutable,
)


def test_provenance_distinct_classifications():
    assert DataClass.REAL != DataClass.DERIVED
    assert DataClass.REAL != DataClass.SYNTHETIC
    assert DataClass.REAL != DataClass.ASSUMED
    assert DataClass.DERIVED != DataClass.SYNTHETIC


def test_prevent_derived_promotion_to_real():
    with pytest.raises(ValueError, match="Cannot promote classification 'DERIVED' to 'REAL'"):
        assert_classification_immutable(DataClass.DERIVED, DataClass.REAL)


def test_prevent_synthetic_promotion_to_real():
    with pytest.raises(ValueError, match="Cannot promote classification 'SYNTHETIC' to 'REAL'"):
        assert_classification_immutable(DataClass.SYNTHETIC, DataClass.REAL)


def test_prevent_synthetic_promotion_to_derived():
    with pytest.raises(ValueError, match="Cannot promote synthetic record to 'DERIVED'"):
        assert_classification_immutable(DataClass.SYNTHETIC, DataClass.DERIVED)


def test_provenance_metadata_derived_requires_method_or_ref():
    with pytest.raises(ValueError, match="DERIVED records must provide either derivation_method or source_reference"):
        ProvenanceMetadata(
            data_class=DataClass.DERIVED,
            source_id="SRC-TEST-01",
            derivation_method=None,
            source_reference=None,
        )


def test_provenance_metadata_valid():
    meta = ProvenanceMetadata(
        data_class=DataClass.REAL,
        source_id="SRC-TAG-2023-TBL-01",
        source_reference="Table 1 Schedule",
    )
    assert meta.data_class == DataClass.REAL
    assert meta.confidence == 1.0
