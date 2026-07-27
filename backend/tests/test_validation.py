from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from backend.pipeline.validation import (
    RecordContext,
    load_validation_rules,
    validate_dataset,
    validate_record,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES = load_validation_rules(PROJECT_ROOT / "backend/config/validation_rules.yaml")


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "external_player_id": "1",
        "source_player_name": "Giocatore",
        "rated_appearances": 10,
        "average_rating": Decimal("6.0"),
        "fantasy_average": Decimal("6.5"),
        "goals_scored": 1,
        "goals_conceded": 0,
        "penalties_saved": 0,
        "penalties_taken": 1,
        "penalties_scored": 1,
        "penalties_missed": 0,
        "assists": 1,
        "yellow_cards": 2,
        "red_cards": 0,
        "own_goals": 0,
    }
    record.update(overrides)
    return record


def _context(
    record: dict[str, object] | None = None,
    *,
    season: str = "2022/2023",
    row: int = 3,
) -> RecordContext:
    return RecordContext(
        season=season,
        source_file="season.xlsx",
        sheet_name="Tutti",
        source_row_number=row,
        record=record or _record(),
    )


def test_valid_record_has_no_issues() -> None:
    assert validate_record(_context(), RULES) == ()


def test_pv_above_configured_season_limit_is_blocking() -> None:
    issues = validate_record(_context(_record(rated_appearances=39)), RULES)

    assert [issue.code for issue in issues] == ["VAL-RANGE-PV"]
    assert issues[0].severity == "error"


def test_penalty_identity_is_blocking() -> None:
    issues = validate_record(
        _context(
            _record(
                penalties_taken=2,
                penalties_scored=1,
                penalties_missed=0,
            )
        ),
        RULES,
    )

    assert any(issue.code == "VAL-PENALTY-IDENTITY" for issue in issues)


def test_lazetic_shape_is_warning_and_not_error() -> None:
    issues = validate_record(
        _context(
            _record(
                rated_appearances=0,
                average_rating=None,
                fantasy_average=None,
                goals_scored=0,
                penalties_taken=0,
                penalties_scored=0,
                yellow_cards=1,
                assists=0,
            )
        ),
        RULES,
    )

    assert [issue.code for issue in issues] == ["VAL-ADDITIVE-WITHOUT-PV"]
    assert issues[0].severity == "warning"


def test_duplicate_player_season_marks_each_duplicate_row() -> None:
    contexts = [_context(row=3), _context(row=4)]

    result = validate_dataset(contexts, RULES)

    duplicates = [
        issue
        for issue in result.errors
        if issue.code == "VAL-DUPLICATE-PLAYER-SEASON"
    ]
    assert len(duplicates) == 2


def test_same_id_in_different_seasons_is_not_duplicate() -> None:
    result = validate_dataset(
        [_context(season="2022/2023"), _context(season="2023/2024")],
        RULES,
    )

    assert result.errors == ()


def test_row_reconciliation_includes_excluded_rows() -> None:
    result = validate_dataset([_context()], RULES, excluded_rows=2)

    assert result.input_rows == 3
    assert result.valid_rows == 1
    assert result.excluded_rows == 2


def test_invalid_validation_configuration_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(
        json.dumps(
            {
                "validation_schema_version": 1,
                "max_rated_appearances": 0,
                "average_rating_min": 10,
                "average_rating_max": 0,
                "warn_additive_with_zero_appearances": True,
                "warn_goals_greater_than_appearances": True,
                "warn_assists_greater_than_appearances": True,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_rated_appearances"):
        load_validation_rules(path)

