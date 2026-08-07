from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.base import Base
from backend.app.db.session import create_database_engine, get_session
from backend.app.main import create_app
from backend.app.models import (
    CurrentSeasonList,
    Player,
    PlayerMappingReview,
    PlayerSeasonStats,
    PlayerTeamSeason,
    Season,
    SourceImport,
    SourceRecord,
    Team,
)


@pytest.fixture
def api(tmp_path: Path) -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        season_old = Season(code="2024/2025", start_year=2024, end_year=2025)
        season_new = Season(code="2025/2026", start_year=2025, end_year=2026)
        roma = Team(display_name="Roma", normalized_name="roma")
        inter = Team(display_name="Inter", normalized_name="inter")
        first = Player(
            external_provider="fantacalcio",
            external_player_id="1",
            display_name="Primo",
            normalized_name="primo",
            matching_status="certain_external_id",
        )
        second = Player(
            external_provider="fantacalcio",
            external_player_id="2",
            display_name="Secondo",
            normalized_name="secondo",
            matching_status="certain_external_id",
        )
        session.add_all([season_old, season_new, roma, inter, first, second])
        session.flush()
        first_old = PlayerSeasonStats(
            player_id=first.id,
            season_id=season_old.id,
            classic_role="C",
            mantra_roles="C",
            rated_appearances=20,
            average_rating=6,
            fantasy_average=6.5,
            goals_scored=2,
            assists=2,
            has_valid_rating=True,
        )
        first_new = PlayerSeasonStats(
            player_id=first.id,
            season_id=season_new.id,
            classic_role="C",
            mantra_roles="C;T",
            rated_appearances=30,
            average_rating=6.5,
            fantasy_average=7,
            goals_scored=5,
            assists=4,
            has_valid_rating=True,
        )
        second_new = PlayerSeasonStats(
            player_id=second.id,
            season_id=season_new.id,
            classic_role="A",
            mantra_roles="Pc",
            rated_appearances=0,
            average_rating=None,
            fantasy_average=None,
            yellow_cards=1,
            has_valid_rating=False,
            quality_status="warning",
            quality_notes="Warning test",
        )
        session.add_all([first_old, first_new, second_new])
        session.flush()
        session.add_all(
            [
                PlayerTeamSeason(
                    player_season_stats_id=first_old.id,
                    team_id=roma.id,
                    association_type="observed",
                ),
                PlayerTeamSeason(
                    player_season_stats_id=first_new.id,
                    team_id=inter.id,
                    association_type="observed",
                ),
                PlayerTeamSeason(
                    player_season_stats_id=second_new.id,
                    team_id=roma.id,
                    association_type="observed",
                ),
            ]
        )
        source_import = SourceImport(
            season_id=season_new.id,
            import_type="season",
            source_filename="season.xlsx",
            source_sha256="a" * 64,
            source_provider="fantacalcio",
            status="completed",
            row_count=1,
        )
        session.add(source_import)
        session.flush()
        source = SourceRecord(
            import_id=source_import.id,
            sheet_name="Tutti",
            source_row_number=3,
            external_player_id="2",
            raw_payload_json={"Id": 2, "Nome": "Secondo"},
            record_hash="b" * 64,
            validation_status="warning",
        )
        session.add(source)
        session.flush()
        session.add(
            PlayerMappingReview(
                source_record_id=source.id,
                candidate_player_id=first.id,
                suggested_player_id=first.id,
                similarity_score=95,
                status="pending",
                reason="Similarità test",
            )
        )
        current_season = Season(
            code="2026/2027", start_year=2026, end_year=2027, is_current=True
        )
        session.add(current_season)
        session.flush()
        current_import = SourceImport(
            season_id=current_season.id,
            import_type="current_list",
            source_filename="listone.xlsx",
            source_sha256="c" * 64,
            source_provider="fantacalcio",
            status="completed",
            row_count=2,
        )
        session.add(current_import)
        session.flush()
        current_sources = []
        for row_number, external_id in enumerate(("1", "2"), start=3):
            current_source = SourceRecord(
                import_id=current_import.id,
                sheet_name="Tutti",
                source_row_number=row_number,
                external_player_id=external_id,
                raw_payload_json={"Id": external_id},
                record_hash=("d" if external_id == "1" else "e") * 64,
                validation_status="valid",
            )
            session.add(current_source)
            current_sources.append(current_source)
        session.flush()
        session.add_all(
            [
                CurrentSeasonList(
                    season_id=current_season.id,
                    player_id=first.id,
                    source_record_id=current_sources[0].id,
                    external_player_id="1",
                    source_name="Primo",
                    official_classic_role="C",
                    official_mantra_roles="C;T",
                    official_team_id=inter.id,
                    quotation=20,
                    initial_quotation=20,
                    mantra_quotation=21,
                    initial_mantra_quotation=21,
                    fvm=200,
                    fvm_mantra=210,
                    mapping_status="certain_external_id",
                ),
                CurrentSeasonList(
                    season_id=current_season.id,
                    player_id=second.id,
                    source_record_id=current_sources[1].id,
                    external_player_id="2",
                    source_name="Secondo",
                    official_classic_role="A",
                    official_mantra_roles="Pc",
                    official_team_id=roma.id,
                    quotation=10,
                    initial_quotation=10,
                    mantra_quotation=10,
                    initial_mantra_quotation=10,
                    fvm=100,
                    fvm_mantra=100,
                    mapping_status="certain_external_id",
                ),
            ]
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client, factory
    engine.dispose()


def test_health_and_openapi(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api
    assert client.get("/health").json() == {"status": "ok"}
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Fantacalcio Analysis API"
    assert "/api/v1/players" in schema["paths"]


def test_seasons_are_chronological(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api
    response = client.get("/api/v1/seasons")
    assert response.status_code == 200
    assert [item["code"] for item in response.json()] == [
        "2024/2025",
        "2025/2026",
        "2026/2027",
    ]
    assert response.json()[-1]["is_current"] is True


def test_player_list_filters_paginates_and_exposes_reliability(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    response = client.get(
        "/api/v1/players",
        params={
            "role": "C",
            "team": "Inter",
            "min_appearances": 20,
            "page_size": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1
    assert body["items"][0]["display_name"] == "Primo"
    assert body["items"][0]["latest_team"] == "Inter"
    assert body["items"][0]["reliability_band"] in {"low", "medium", "high"}


def test_player_detail_history_and_missing_player(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    detail = client.get("/api/v1/players/1")
    assert detail.status_code == 200
    assert len(detail.json()["history"]) == 2
    assert detail.json()["metrics"]["total_pv"] == 50
    history = client.get("/api/v1/players/1/history")
    assert [item["season"] for item in history.json()] == [
        "2024/2025",
        "2025/2026",
    ]
    missing = client.get("/api/v1/players/999")
    assert missing.status_code == 404
    assert missing.json()["error"] == "http_error"


def test_compare_requires_distinct_existing_players(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    response = client.get(
        "/api/v1/players/compare",
        params=[("ids", 1), ("ids", 2)],
    )
    assert response.status_code == 200
    assert len(response.json()["players"]) == 2
    duplicate = client.get(
        "/api/v1/players/compare",
        params=[("ids", 1), ("ids", 1)],
    )
    assert duplicate.status_code == 422


def test_quality_and_pending_mapping_endpoints(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    issues = client.get("/api/v1/data-quality/issues").json()
    assert {issue["category"] for issue in issues} == {
        "data_quality",
        "player_mapping",
    }
    pending = client.get("/api/v1/player-mappings/pending")
    assert pending.status_code == 200
    assert pending.json()[0]["source_name"] == "Secondo"
    assert pending.json()[0]["source_role"] is None
    assert pending.json()[0]["candidate"]["display_name"] == "Primo"
    assert pending.json()[0]["candidate"]["roles"] == ["C"]


def test_mapping_resolution_is_persisted_and_cannot_be_repeated(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = api
    response = client.post(
        "/api/v1/player-mappings/1/resolve",
        json={"resolution": "new_player", "notes": "Identità distinta"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    with factory() as session:
        review = session.get(PlayerMappingReview, 1)
        assert review is not None
        assert review.resolved_player_id == 2
        assert review.notes == "Identità distinta"
    repeated = client.post(
        "/api/v1/player-mappings/1/resolve",
        json={"resolution": "new_player"},
    )
    assert repeated.status_code == 409


def test_merge_preview_blocks_overlapping_seasons(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    preview = client.get("/api/v1/player-mappings/1/merge-preview")
    assert preview.status_code == 200
    assert preview.json()["blocked"] is True
    assert "Statistiche presenti" in preview.json()["blockers"][0]


def test_invalid_query_has_consistent_error_shape(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    response = client.get("/api/v1/players", params={"page_size": 1000})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_ranking_metadata_and_transparent_calculation(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    metadata = client.get("/api/v1/rankings")
    assert metadata.status_code == 200
    assert metadata.json()["normalization"] == "percentile"

    response = client.post(
        "/api/v1/rankings/calculate",
        json={
            "role": "C",
            "selected_seasons": ["2024/2025", "2025/2026"],
            "minimum_appearances": 1,
            "recency_decay": 0.75,
            "continuity_threshold": 19,
            "metric_weights": {
                "fantasy_average_recency_weighted": 2,
                "reliability_score": 0,
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["initial_pool_size"] == 1
    assert body["items"][0]["display_name"] == "Primo"
    assert body["items"][0]["score"] == 100
    component = body["items"][0]["metrics"][
        "fantasy_average_recency_weighted"
    ]
    assert component["weight"] == 2
    assert component["contribution"] == 100


def test_ranking_rejects_unknown_metric(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api
    response = client.post(
        "/api/v1/rankings/calculate",
        json={
            "role": "C",
            "selected_seasons": ["2025/2026"],
            "metric_weights": {"invented_metric": 1},
        },
    )
    assert response.status_code == 422
    assert "non supportate" in response.json()["detail"]


def test_ranking_config_crud(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api
    payload = {
        "name": "Mia classifica C",
        "configuration": {
            "role": "C",
            "selected_seasons": ["2025/2026"],
            "minimum_appearances": 10,
            "recency_decay": 0.75,
            "continuity_threshold": 19,
            "metric_weights": {"continuity": 1},
        },
    }
    created = client.post("/api/v1/ranking-configs", json=payload)
    assert created.status_code == 201
    config_id = created.json()["id"]
    assert client.get("/api/v1/ranking-configs").json()[0]["name"] == payload["name"]

    payload["name"] = "Classifica aggiornata"
    updated = client.put(f"/api/v1/ranking-configs/{config_id}", json=payload)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Classifica aggiornata"

    deleted = client.delete(f"/api/v1/ranking-configs/{config_id}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/ranking-configs").json() == []
