from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.pipeline.matching import (
    ManualMapping,
    PlayerMatcher,
    load_manual_mappings,
    match_records,
)


def _record(
    external_id: str,
    name: str,
    *,
    match_key: str | None = None,
    role: str = "C",
    team: str = "Team",
) -> dict[str, object]:
    return {
        "external_player_id": external_id,
        "source_player_name": name,
        "normalized_player_name": name.casefold(),
        "player_match_key": match_key or name.casefold(),
        "classic_role": role,
        "source_team_name": team,
    }


def test_same_external_id_is_a_certain_match_and_collects_aliases() -> None:
    result = match_records(
        [
            ("2022/2023", _record("5734", "Soule'", match_key="soule")),
            ("2023/2024", _record("5734", "Soulè", match_key="soule")),
        ],
        provider="fantacalcio",
    )

    assert len(result.identities) == 1
    assert [decision.status for decision in result.decisions] == [
        "new_player",
        "certain_external_id",
    ]
    assert result.identities[0].aliases == {"Soule'", "Soulè"}
    assert result.reviews == ()


def test_identical_name_with_different_ids_is_not_merged() -> None:
    result = match_records(
        [
            ("2022/2023", _record("5859", "Ndiaye")),
            ("2025/2026", _record("7202", "Ndiaye")),
        ],
        provider="fantacalcio",
    )

    assert len(result.identities) == 2
    assert len(result.reviews) == 1
    assert result.reviews[0].review_type == "homonym"
    assert result.reviews[0].candidates[0].score == 100


def test_fuzzy_similarity_only_creates_a_review() -> None:
    result = match_records(
        [
            ("2022/2023", _record("1", "Mario Rossi", match_key="mario rossi")),
            ("2023/2024", _record("2", "Mário Rossi", match_key="mario rossi")),
        ],
        provider="fantacalcio",
    )

    assert len(result.identities) == 2
    assert result.decisions[1].status == "new_player"
    assert result.reviews[0].review_type == "homonym"


def test_below_threshold_creates_new_identity_without_review() -> None:
    result = match_records(
        [
            ("2022/2023", _record("1", "Mario Rossi")),
            ("2023/2024", _record("2", "Luigi Bianchi")),
        ],
        provider="fantacalcio",
        fuzzy_threshold=92,
    )

    assert len(result.identities) == 2
    assert result.reviews == ()


def test_manual_mapping_is_the_only_non_id_automatic_link() -> None:
    matcher = PlayerMatcher(
        [
            ManualMapping(
                source_provider="future-list",
                source_external_id="ABC",
                target_provider="fantacalcio",
                target_external_id="5734",
                note="Confermato manualmente",
            )
        ]
    )
    first = matcher.add_record(
        _record("5734", "Soulè", match_key="soule"),
        season="2023/2024",
        provider="fantacalcio",
    )
    second = matcher.add_record(
        _record("ABC", "Matias Soulé", match_key="matias soule"),
        season="2026/2027",
        provider="future-list",
    )

    assert second.status == "manual_confirmed"
    assert second.internal_key == first.internal_key
    assert len(matcher.result().identities) == 1


def test_manual_mapping_file_rejects_duplicate_sources(tmp_path: Path) -> None:
    item = {
        "source_provider": "future-list",
        "source_external_id": "1",
        "target_provider": "fantacalcio",
        "target_external_id": "2",
    }
    path = tmp_path / "mappings.json"
    path.write_text(
        json.dumps(
            {
                "mapping_schema_version": 1,
                "provider": "fantacalcio",
                "mappings": [item, item],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="più mapping manuali"):
        load_manual_mappings(path)


def test_roles_and_teams_are_historical_context_not_identity_keys() -> None:
    result = match_records(
        [
            (
                "2022/2023",
                _record("5800", "Gudmundsson A.", role="C", team="Genoa"),
            ),
            (
                "2024/2025",
                _record("5800", "Gudmundsson A.", role="A", team="Fiorentina"),
            ),
        ],
        provider="fantacalcio",
    )

    identity = result.identities[0]
    assert len(result.identities) == 1
    assert identity.roles == {"C", "A"}
    assert identity.teams == {"Genoa", "Fiorentina"}

