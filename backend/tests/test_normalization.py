from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from backend.pipeline.column_mapping import load_column_mapping
from backend.pipeline.normalization import (
    NormalizationError,
    normalize_mantra_roles,
    normalize_name,
    normalize_source_record,
    normalize_team,
    parse_decimal,
    parse_integer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPPING = load_column_mapping(PROJECT_ROOT / "backend/config/column_mapping.yaml")


def _source_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "Id": 2762,
        "R": "C",
        "Rm": "W;A",
        "Nome": "  Kouame\u0300  ",
        "Squadra": "  Fiorentina ",
        "Pv": 20,
        "Mv": 6.15,
        "Fm": 6.5,
        "Gf": 2,
        "Gs": 0,
        "Rp": 0,
        "Rc": 1,
        "R+": 1,
        "R-": 0,
        "Ass": 3,
        "Amm": 2,
        "Esp": 0,
        "Au": 0,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("6,25", Decimal("6.25")),
        ("1.234,50", Decimal("1234.50")),
        ("6.25", Decimal("6.25")),
        (6.25, Decimal("6.25")),
        ("  ", None),
        ("-", None),
        ("N.D.", None),
        ("n/a", None),
    ],
)
def test_parse_decimal_handles_italian_and_null_values(
    source: object,
    expected: Decimal | None,
) -> None:
    assert parse_decimal(source) == expected


def test_percentage_requires_explicit_permission() -> None:
    assert parse_decimal("25%", allow_percentage=True) == Decimal("0.25")
    with pytest.raises(NormalizationError, match="Percentuale non ammessa"):
        parse_decimal("25%")


def test_integer_rejects_decimal_fraction() -> None:
    assert parse_integer("12,0") == 12
    with pytest.raises(NormalizationError, match="Intero atteso"):
        parse_integer("12,5")


def test_name_normalization_preserves_display_but_builds_permissive_key() -> None:
    name = normalize_name("  D\u2019Ambro\u0301sio  ")

    assert name.display == "D'Ambrósio"
    assert name.normalized == "d'ambrósio"
    assert name.match_key == "d ambrosio"


def test_team_normalization_does_not_apply_unverified_aliases() -> None:
    display, normalized = normalize_team("  Hèllas   Verona ")

    assert display == "Hèllas Verona"
    assert normalized == "hellas verona"


def test_mantra_roles_keep_source_order_and_remove_duplicates() -> None:
    assert normalize_mantra_roles(" Dd ; Dc ; Dd ") == ("Dd", "Dc")
    with pytest.raises(NormalizationError, match="Ruolo Mantra"):
        normalize_mantra_roles("Dd;Sconosciuto")


def test_record_keeps_raw_canonical_and_analytical_layers() -> None:
    source = _source_row()

    result = normalize_source_record(source, MAPPING)

    assert result.raw["Nome"] == "  Kouame\u0300  "
    assert result.canonical_source["source_player_name"] == "  Kouame\u0300  "
    assert result.analytical["source_player_name"] == "Kouamè"
    assert result.analytical["player_match_key"] == "kouame"
    assert result.analytical["mantra_roles"] == ("W", "A")
    assert result.analytical["average_rating"] == Decimal("6.15")


def test_zero_pv_converts_only_averages_to_null() -> None:
    result = normalize_source_record(
        _source_row(Pv=0, Mv=0, Fm=0, Gf=0, Ass=0, Amm=1),
        MAPPING,
    )

    assert result.canonical_source["average_rating"] == 0
    assert result.analytical["average_rating"] is None
    assert result.analytical["fantasy_average"] is None
    assert result.analytical["yellow_cards"] == 1
    assert result.analytical["has_valid_rating"] is False


def test_negative_additive_stat_is_rejected() -> None:
    with pytest.raises(NormalizationError, match="goals_scored"):
        normalize_source_record(_source_row(Gf=-1), MAPPING)


def test_missing_season_is_not_synthesized() -> None:
    rows = [_source_row(Id=1), _source_row(Id=2)]

    normalized = [normalize_source_record(row, MAPPING) for row in rows]

    assert len(normalized) == 2
    assert {row.analytical["external_player_id"] for row in normalized} == {"1", "2"}
