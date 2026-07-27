from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.pipeline.column_mapping import (
    canonicalize_record,
    load_column_mapping,
    validate_headers,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = PROJECT_ROOT / "backend/config/column_mapping.yaml"


def test_project_mapping_is_complete_and_unique() -> None:
    mapping = load_column_mapping(MAPPING_PATH)

    assert mapping.schema_version == 1
    assert mapping.provider == "fantacalcio"
    assert len(mapping.columns) == 18
    assert len(set(mapping.source_columns)) == 18
    assert len(set(mapping.canonical_columns)) == 18
    assert mapping.by_source()["Mv"].weight_column == "Pv"
    assert mapping.by_source()["Fm"].zero_policy == "null_when_pv_zero"
    assert mapping.by_source()["Squadra"].semantic_status == "user_confirmed"


@pytest.mark.parametrize(
    ("actual", "missing", "unexpected", "duplicate", "order_matches"),
    [
        (("Id", "Nome"), (), (), (), True),
        (("Id",), ("Nome",), (), (), False),
        (("Id", "Nome", "Extra"), (), ("Extra",), (), False),
        (("Id", "Nome", "Nome"), (), (), ("Nome",), False),
        (("Nome", "Id"), (), (), (), False),
    ],
)
def test_header_validation_reports_every_difference(
    tmp_path: Path,
    actual: tuple[str, ...],
    missing: tuple[str, ...],
    unexpected: tuple[str, ...],
    duplicate: tuple[str, ...],
    order_matches: bool,
) -> None:
    path = tmp_path / "mapping.yaml"
    path.write_text(
        json.dumps(
            {
                "mapping_schema_version": 1,
                "provider": "test",
                "applies_to": ["2022/2023"],
                "columns": [
                    {
                        "source": source,
                        "canonical": canonical,
                        "data_type": "string",
                        "nullable": False,
                        "category": "test",
                        "aggregation": "not_applicable",
                        "zero_policy": "not_applicable",
                        "semantic_status": "test",
                        "description": "Test column",
                    }
                    for source, canonical in (
                        ("Id", "external_id"),
                        ("Nome", "name"),
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    mapping = load_column_mapping(path)

    result = validate_headers(actual, mapping)

    assert result.missing == missing
    assert result.unexpected == unexpected
    assert result.duplicate == duplicate
    assert result.order_matches is order_matches
    assert result.is_valid is not (missing or unexpected or duplicate)


def test_mapping_rejects_duplicate_canonical_names(tmp_path: Path) -> None:
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    raw["columns"][1]["canonical"] = raw["columns"][0]["canonical"]
    path = tmp_path / "mapping.yaml"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="Colonne canoniche duplicate"):
        load_column_mapping(path)


def test_mapping_rejects_unknown_weight_column(tmp_path: Path) -> None:
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    raw["columns"][6]["weight_column"] = "VotiInesistenti"
    path = tmp_path / "mapping.yaml"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="Colonne peso non definite"):
        load_column_mapping(path)


def test_canonicalize_record_only_renames_fields() -> None:
    mapping = load_column_mapping(MAPPING_PATH)
    source = {
        definition.source: index
        for index, definition in enumerate(mapping.columns)
    }

    canonical = canonicalize_record(source, mapping)

    assert list(canonical) == list(mapping.canonical_columns)
    assert canonical["external_player_id"] == 0
    assert canonical["own_goals"] == 17
    assert source["Mv"] == canonical["average_rating"]

