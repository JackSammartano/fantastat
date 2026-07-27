from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.session import create_database_engine
from backend.app.models import (
    Player,
    PlayerAlias,
    PlayerMappingReview,
    PlayerSeasonStats,
    PlayerTeamSeason,
    Season,
    SourceImport,
    SourceRecord,
    Team,
)
from backend.pipeline.importer import (
    PreparedRecord,
    persist_prepared_batch,
    record_hash,
)
from backend.pipeline.matching import match_records


def _analytical(
    external_id: str,
    name: str,
    *,
    pv: int = 10,
    team: str = "Roma",
) -> dict[str, object]:
    return {
        "external_player_id": external_id,
        "source_player_name": name,
        "normalized_player_name": name.casefold(),
        "player_match_key": name.casefold(),
        "source_team_name": team,
        "normalized_team_name": team.casefold(),
        "classic_role": "C",
        "mantra_roles": ("C",),
        "rated_appearances": pv,
        "average_rating": 6 if pv else None,
        "fantasy_average": 6.5 if pv else None,
        "goals_scored": 1 if pv else 0,
        "goals_conceded": 0,
        "penalties_saved": 0,
        "penalties_taken": 0,
        "penalties_scored": 0,
        "penalties_missed": 0,
        "assists": 1 if pv else 0,
        "yellow_cards": 1,
        "red_cards": 0,
        "own_goals": 0,
        "has_valid_rating": pv > 0,
    }


def _prepared(
    season: str,
    analytical: dict[str, object],
    *,
    sha: str,
    row: int = 3,
    quality_status: str = "valid",
) -> PreparedRecord:
    start, end = map(int, season.split("/"))
    return PreparedRecord(
        season_code=season,
        start_year=start,
        end_year=end,
        source_file=f"season-{start}.xlsx",
        source_sha256=sha,
        sheet_name="Tutti",
        source_row_number=row,
        raw={"Id": analytical["external_player_id"], "Nome": analytical["source_player_name"]},
        analytical=analytical,
        quality_status=quality_status,
        quality_notes="warning test" if quality_status == "warning" else None,
    )


def _count(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_record_hash_is_independent_from_dictionary_order() -> None:
    assert record_hash({"Id": 1, "Nome": "Test"}) == record_hash(
        {"Nome": "Test", "Id": 1}
    )


def test_batch_persists_history_and_is_idempotent(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'import.db'}")
    Base.metadata.create_all(engine)
    first = _analytical("5734", "Soule'")
    second = _analytical("5734", "Soulè", team="Frosinone")
    prepared = [
        _prepared("2022/2023", first, sha="a" * 64),
        _prepared("2023/2024", second, sha="b" * 64),
    ]
    matching = match_records(
        [("2022/2023", first), ("2023/2024", second)],
        provider="fantacalcio",
    )

    with Session(engine) as session, session.begin():
        summary = persist_prepared_batch(
            session, prepared, matching, provider="fantacalcio"
        )

    assert summary.status == "completed"
    assert summary.imported_rows == 2
    assert summary.players_created == 1
    with Session(engine) as session:
        assert _count(session, Player) == 1
        assert _count(session, Season) == 2
        assert _count(session, Team) == 2
        assert _count(session, SourceImport) == 2
        assert _count(session, SourceRecord) == 2
        assert _count(session, PlayerSeasonStats) == 2
        assert _count(session, PlayerTeamSeason) == 2
        assert _count(session, PlayerAlias) == 2

    with Session(engine) as session, session.begin():
        second_summary = persist_prepared_batch(
            session, prepared, matching, provider="fantacalcio"
        )

    assert second_summary.status == "already_imported"
    assert second_summary.imported_rows == 0
    with Session(engine) as session:
        assert _count(session, SourceRecord) == 2
        assert _count(session, PlayerSeasonStats) == 2
    engine.dispose()


def test_warning_quality_and_homonym_review_are_persisted(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'review.db'}")
    Base.metadata.create_all(engine)
    first = _analytical("5859", "Ndiaye")
    second = _analytical("7202", "Ndiaye", pv=0)
    prepared = [
        _prepared("2022/2023", first, sha="a" * 64),
        _prepared(
            "2025/2026",
            second,
            sha="b" * 64,
            quality_status="warning",
        ),
    ]
    matching = match_records(
        [("2022/2023", first), ("2025/2026", second)],
        provider="fantacalcio",
    )

    with Session(engine) as session, session.begin():
        summary = persist_prepared_batch(
            session, prepared, matching, provider="fantacalcio"
        )

    assert summary.mapping_reviews_created == 1
    with Session(engine) as session:
        assert _count(session, Player) == 2
        assert _count(session, PlayerMappingReview) == 1
        warning_stats = session.scalar(
            select(PlayerSeasonStats).where(
                PlayerSeasonStats.quality_status == "warning"
            )
        )
        assert warning_stats is not None
        assert warning_stats.average_rating is None
        warning_source = session.scalar(
            select(SourceRecord).where(SourceRecord.validation_status == "warning")
        )
        assert warning_source is not None
    engine.dispose()


def test_failed_batch_rolls_back_the_entire_transaction(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'rollback.db'}")
    Base.metadata.create_all(engine)
    first = _analytical("1", "Primo")
    second = _analytical("2", "Secondo")
    first_prepared = _prepared("2022/2023", first, sha="a" * 64, row=3)
    second_prepared = replace(
        _prepared("2022/2023", second, sha="a" * 64, row=4),
        raw=first_prepared.raw,
    )
    matching = match_records(
        [("2022/2023", first), ("2022/2023", second)],
        provider="fantacalcio",
    )

    with pytest.raises(IntegrityError):
        with Session(engine) as session, session.begin():
            persist_prepared_batch(
                session,
                [first_prepared, second_prepared],
                matching,
                provider="fantacalcio",
            )

    with Session(engine) as session:
        assert _count(session, Player) == 0
        assert _count(session, SourceImport) == 0
        assert _count(session, SourceRecord) == 0
        assert _count(session, PlayerSeasonStats) == 0
    engine.dispose()
