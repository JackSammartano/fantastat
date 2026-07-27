from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.session import create_database_engine
from backend.app.models import (
    Player,
    PlayerAlias,
    PlayerMappingReview,
    PlayerSeasonStats,
    Season,
    SourceImport,
    SourceRecord,
)
from backend.app.services.player_merges import (
    apply_merge,
    merge_preview,
    revert_merge,
)


def test_preview_apply_and_revert_merge_are_auditable(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'merge.db'}")
    Base.metadata.create_all(engine)
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(
        json.dumps({"mapping_schema_version": 1, "mappings": []}),
        encoding="utf-8",
    )
    with Session(engine, expire_on_commit=False) as session:
        old = Season(code="2024/2025", start_year=2024, end_year=2025)
        new = Season(code="2025/2026", start_year=2025, end_year=2026)
        source_player = Player(
            external_provider="fantacalcio",
            external_player_id="20",
            display_name="Nome breve",
            normalized_name="nome breve",
            matching_status="new_player",
        )
        target_player = Player(
            external_provider="fantacalcio",
            external_player_id="10",
            display_name="Nome completo",
            normalized_name="nome completo",
            matching_status="certain_external_id",
        )
        session.add_all([old, new, source_player, target_player])
        session.flush()
        source_stats = PlayerSeasonStats(
            player_id=source_player.id,
            season_id=new.id,
            classic_role="C",
            mantra_roles="C",
            rated_appearances=12,
            average_rating=6.0,
            fantasy_average=6.5,
            has_valid_rating=True,
        )
        target_stats = PlayerSeasonStats(
            player_id=target_player.id,
            season_id=old.id,
            classic_role="C",
            mantra_roles="C",
            rated_appearances=20,
            average_rating=6.1,
            fantasy_average=6.7,
            has_valid_rating=True,
        )
        alias = PlayerAlias(
            player_id=source_player.id,
            source_name="Nome breve",
            normalized_name="nome breve",
            source_provider="fantacalcio",
            first_seen_season_id=new.id,
            last_seen_season_id=new.id,
        )
        source_import = SourceImport(
            season_id=new.id,
            import_type="season",
            source_filename="test.xlsx",
            source_sha256="c" * 64,
            source_provider="fantacalcio",
            status="completed",
        )
        session.add_all([source_stats, target_stats, alias, source_import])
        session.flush()
        record = SourceRecord(
            import_id=source_import.id,
            sheet_name="Tutti",
            source_row_number=3,
            external_player_id="20",
            raw_payload_json={"Nome": "Nome breve"},
            record_hash="d" * 64,
            validation_status="valid",
        )
        session.add(record)
        session.flush()
        review = PlayerMappingReview(
            source_record_id=record.id,
            candidate_player_id=target_player.id,
            similarity_score=95,
            status="pending",
            reason="Test",
        )
        session.add(review)
        session.commit()

        preview = merge_preview(session, review.id)
        assert preview["blocked"] is False
        assert preview["seasons_to_move"] == ["2025/2026"]

        audit = apply_merge(
            session,
            review.id,
            preview["preview_token"],
            mapping_path=mapping_path,
        )
        assert session.get(PlayerSeasonStats, source_stats.id).player_id == target_player.id
        assert audit.status == "applied"
        assert json.loads(mapping_path.read_text())["mappings"][0][
            "source_external_id"
        ] == "20"

        reverted = revert_merge(session, audit.id, mapping_path=mapping_path)
        assert reverted.status == "reverted"
        assert session.get(PlayerSeasonStats, source_stats.id).player_id == source_player.id
        assert json.loads(mapping_path.read_text())["mappings"] == []
        assert session.get(PlayerMappingReview, review.id).status == "pending"
    engine.dispose()
