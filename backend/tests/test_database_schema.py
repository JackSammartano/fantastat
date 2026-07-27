from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.session import create_database_engine
from backend.app.models import Player, PlayerSeasonStats, Season, SourceImport


EXPECTED_TABLES = {
    "current_season_list",
    "player_aliases",
    "player_mapping_reviews",
    "player_merge_audits",
    "player_season_stats",
    "player_team_seasons",
    "players",
    "ranking_configs",
    "seasons",
    "source_imports",
    "source_records",
    "teams",
}


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session
    engine.dispose()


def test_schema_contains_all_expected_tables(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'schema.db'}")
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES
    assert inspect(engine).get_foreign_keys("player_season_stats")
    assert inspect(engine).get_unique_constraints("player_season_stats")
    engine.dispose()


def test_season_years_must_be_consecutive(session: Session) -> None:
    session.add(Season(code="2022/2024", start_year=2022, end_year=2024))

    with pytest.raises(IntegrityError):
        session.commit()


def test_player_season_is_unique(session: Session) -> None:
    player = Player(
        external_provider="fantacalcio",
        external_player_id="572",
        display_name="Meret",
        normalized_name="meret",
        matching_status="certain_external_id",
    )
    season = Season(code="2022/2023", start_year=2022, end_year=2023)
    session.add_all([player, season])
    session.flush()
    common = {
        "player_id": player.id,
        "season_id": season.id,
        "classic_role": "P",
        "mantra_roles": "Por",
        "rated_appearances": 34,
        "average_rating": 6.18,
        "fantasy_average": 5.56,
        "has_valid_rating": True,
    }
    session.add_all([PlayerSeasonStats(**common), PlayerSeasonStats(**common)])

    with pytest.raises(IntegrityError):
        session.commit()


def test_zero_appearances_require_null_averages(session: Session) -> None:
    player = Player(
        external_provider="fantacalcio",
        external_player_id="5785",
        display_name="Lazetic",
        normalized_name="lazetic",
    )
    season = Season(code="2022/2023", start_year=2022, end_year=2023)
    session.add_all([player, season])
    session.flush()
    session.add(
        PlayerSeasonStats(
            player_id=player.id,
            season_id=season.id,
            classic_role="A",
            mantra_roles="Pc",
            rated_appearances=0,
            average_rating=0,
            fantasy_average=0,
            yellow_cards=1,
            has_valid_rating=False,
            quality_status="warning",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_zero_appearances_allow_additive_stats_with_null_averages(
    session: Session,
) -> None:
    player = Player(
        external_provider="fantacalcio",
        external_player_id="5785",
        display_name="Lazetic",
        normalized_name="lazetic",
    )
    season = Season(code="2022/2023", start_year=2022, end_year=2023)
    session.add_all([player, season])
    session.flush()
    session.add(
        PlayerSeasonStats(
            player_id=player.id,
            season_id=season.id,
            classic_role="A",
            mantra_roles="Pc",
            rated_appearances=0,
            average_rating=None,
            fantasy_average=None,
            yellow_cards=1,
            has_valid_rating=False,
            quality_status="warning",
        )
    )

    session.commit()
    assert session.query(PlayerSeasonStats).one().yellow_cards == 1


def test_penalty_identity_is_enforced(session: Session) -> None:
    player = Player(
        external_provider="fantacalcio",
        external_player_id="1",
        display_name="Test",
        normalized_name="test",
    )
    season = Season(code="2022/2023", start_year=2022, end_year=2023)
    session.add_all([player, season])
    session.flush()
    session.add(
        PlayerSeasonStats(
            player_id=player.id,
            season_id=season.id,
            classic_role="A",
            mantra_roles="Pc",
            rated_appearances=1,
            average_rating=6,
            fantasy_average=6,
            penalties_taken=2,
            penalties_scored=1,
            penalties_missed=0,
            has_valid_rating=True,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_source_import_hash_is_idempotency_key(session: Session) -> None:
    common = {
        "import_type": "season",
        "source_filename": "season.xlsx",
        "source_sha256": "a" * 64,
        "source_provider": "fantacalcio",
    }
    session.add_all([SourceImport(**common), SourceImport(**common)])

    with pytest.raises(IntegrityError):
        session.commit()
