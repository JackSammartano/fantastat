from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.session import create_database_engine
from backend.app.models import CurrentSeasonList, Player, SourceImport, SourceRecord
from backend.pipeline.current_list import (
    CurrentListConfig,
    PreparedCurrentPlayer,
    normalize_current_player,
    persist_current_list,
)


def _raw(external_id: int = 1) -> dict[str, object]:
    return {
        "Id": external_id,
        "R": "C",
        "RM": "C;T",
        "Nome": "Giocatore",
        "Squadra": "Roma",
        "Qt.A": 12,
        "Qt.I": 10,
        "Diff.": 2,
        "Qt.A M": 13,
        "Qt.I M": 10,
        "Diff.M": 3,
        "FVM": 100,
        "FVM M": 110,
    }


def _config() -> CurrentListConfig:
    return CurrentListConfig(
        season_code="2026/2027",
        source_file=Path("listone.xlsx"),
        source_provider="fantacalcio",
        canonical_sheet="Tutti",
        ceded_sheet="Ceduti",
        header_row=2,
        role_sheets={},
        expected_columns=tuple(_raw()),
    )


def test_normalization_preserves_all_valuations() -> None:
    row = normalize_current_player(_raw(), 3)

    assert row.external_player_id == "1"
    assert row.mantra_roles == ("C", "T")
    assert row.quotation == Decimal("12")
    assert row.initial_mantra_quotation == Decimal("10")
    assert row.fvm_mantra == Decimal("110")


def test_normalization_rejects_inconsistent_difference() -> None:
    raw = _raw()
    raw["Diff."] = 99

    with pytest.raises(ValueError, match="Diff"):
        normalize_current_player(raw, 3)


def test_persistence_links_id_creates_new_player_and_is_idempotent(
    tmp_path: Path,
) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'current.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add(
            Player(
                external_provider="fantacalcio",
                external_player_id="1",
                display_name="Storico",
                normalized_name="storico",
                matching_status="certain_external_id",
            )
        )

    first = normalize_current_player(_raw(1), 3)
    second_raw = _raw(2)
    second_raw["Nome"] = "Nuovo"
    second = normalize_current_player(second_raw, 4)
    with Session(engine) as session, session.begin():
        summary = persist_current_list(
            session,
            [first, second],
            _config(),
            source_sha256="a" * 64,
            ceded_rows=5,
        )

    assert summary.linked_existing_players == 1
    assert summary.new_players_created == 1
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(CurrentSeasonList)) == 2
        assert session.scalar(select(func.count()).select_from(SourceRecord)) == 2
        new_player = session.scalar(
            select(Player).where(Player.external_player_id == "2")
        )
        assert new_player is not None
        assert new_player.matching_status == "new_player"
        values = session.scalar(
            select(CurrentSeasonList).where(CurrentSeasonList.player_id == new_player.id)
        )
        assert values is not None
        assert values.fvm == 100
        assert values.mantra_quotation == 13

    with Session(engine) as session, session.begin():
        repeated = persist_current_list(
            session,
            [first, second],
            _config(),
            source_sha256="a" * 64,
            ceded_rows=5,
        )
    assert repeated.status == "already_imported"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(SourceImport)) == 1
        assert session.scalar(select(func.count()).select_from(CurrentSeasonList)) == 2
    engine.dispose()
