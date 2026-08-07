from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.session import create_database_engine
from backend.app.models import (
    CurrentSeasonList,
    Player,
    PlayerSeasonStats,
    Season,
    SourceImport,
    SourceRecord,
    Team,
)
from backend.app.services.current_list_queries import list_current_players


def test_current_list_filters_sorts_and_counts_history(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'queries.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        old = Season(code="2025/2026", start_year=2025, end_year=2026)
        current = Season(code="2026/2027", start_year=2026, end_year=2027, is_current=True)
        inter = Team(display_name="Inter", normalized_name="inter")
        roma = Team(display_name="Roma", normalized_name="roma")
        historical = Player(external_provider="fantacalcio", external_player_id="1", display_name="Storico", normalized_name="storico", matching_status="certain_external_id")
        newcomer = Player(external_provider="fantacalcio", external_player_id="2", display_name="Nuovo", normalized_name="nuovo", matching_status="new_player")
        session.add_all([old, current, inter, roma, historical, newcomer])
        session.flush()
        session.add(PlayerSeasonStats(player_id=historical.id, season_id=old.id, classic_role="C", mantra_roles="C", rated_appearances=10, average_rating=6, fantasy_average=6.5, has_valid_rating=True))
        source_import = SourceImport(season_id=current.id, import_type="current_list", source_filename="list.xlsx", source_sha256="a" * 64, source_provider="fantacalcio", status="completed", row_count=2)
        session.add(source_import)
        session.flush()
        sources = []
        for row_number, external_id in enumerate(("1", "2"), start=3):
            source = SourceRecord(import_id=source_import.id, sheet_name="Tutti", source_row_number=row_number, external_player_id=external_id, raw_payload_json={"Id": external_id}, record_hash=external_id * 64, validation_status="valid")
            session.add(source)
            sources.append(source)
        session.flush()
        session.add_all([
            CurrentSeasonList(season_id=current.id, player_id=historical.id, source_record_id=sources[0].id, external_player_id="1", source_name="Storico", official_classic_role="C", official_mantra_roles="C;T", official_team_id=inter.id, quotation=20, initial_quotation=18, mantra_quotation=21, initial_mantra_quotation=18, fvm=200, fvm_mantra=210, mapping_status="certain_external_id"),
            CurrentSeasonList(season_id=current.id, player_id=newcomer.id, source_record_id=sources[1].id, external_player_id="2", source_name="Nuovo", official_classic_role="A", official_mantra_roles="Pc", official_team_id=roma.id, quotation=10, initial_quotation=10, mantra_quotation=10, initial_mantra_quotation=10, fvm=100, fvm_mantra=100, mapping_status="new_player"),
        ])

    with Session(engine) as session:
        result = list_current_players(session, role="C", team="inter", page_size=10)
        assert result["total_items"] == 1
        assert result["items"][0]["name"] == "Storico"
        assert result["items"][0]["quotation_change"] == 2
        assert result["items"][0]["historical_seasons"] == 1

        newcomers = list_current_players(session, mapping_status="new_player", page_size=10)
        assert newcomers["items"][0]["historical_seasons"] == 0
        assert newcomers["items"][0]["name"] == "Nuovo"
    engine.dispose()
