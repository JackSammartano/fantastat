from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.session import get_session
from backend.app.models import (
    Player,
    PlayerMappingReview,
    RankingConfig,
    Season,
    SourceImport,
    SourceRecord,
)
from backend.app.schemas.api import (
    CompareResponse,
    CurrentListPage,
    DataQualityIssueResponse,
    PendingMappingResponse,
    PlayerDetailResponse,
    PlayerHistoryItem,
    PlayerPage,
    ResolveMappingRequest,
    ResolveMappingResponse,
    ApplyMergeRequest,
    MergeAuditResponse,
    SeasonResponse,
    RankingRequest,
    RankingResponse,
    RankingConfigCreate,
    RankingConfigResponse,
)
from backend.app.services.current_list_queries import list_current_players
from backend.app.services.player_merges import (
    apply_merge,
    merge_preview,
    revert_merge,
)
from backend.analytics.ranking import METRIC_DIRECTIONS, METRIC_ROLES
from backend.app.services.player_queries import (
    calculate_players_ranking,
    list_players,
    player_detail,
    player_history,
)


router = APIRouter(prefix="/api/v1")
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("/seasons", response_model=list[SeasonResponse])
def get_seasons(session: DatabaseSession) -> list[Season]:
    return list(session.scalars(select(Season).order_by(Season.start_year)))


@router.get("/rankings")
def get_ranking_metadata() -> dict:
    return {
        "normalization": "percentile",
        "metrics": [
            {
                "key": key,
                "direction": direction,
                "roles": list(METRIC_ROLES.get(key, ("P", "D", "C", "A"))),
            }
            for key, direction in METRIC_DIRECTIONS.items()
        ],
    }


@router.post("/rankings/calculate", response_model=RankingResponse)
def post_calculate_ranking(
    payload: RankingRequest,
    session: DatabaseSession,
) -> dict:
    try:
        return calculate_players_ranking(
            session,
            role=payload.role,
            selected_seasons=payload.selected_seasons,
            minimum_appearances=payload.minimum_appearances,
            recency_decay=payload.recency_decay,
            continuity_threshold=payload.continuity_threshold,
            metric_weights=payload.metric_weights,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/ranking-configs", response_model=list[RankingConfigResponse])
def get_ranking_configs(
    session: DatabaseSession,
    role: Annotated[Literal["P", "D", "C", "A"] | None, Query()] = None,
) -> list[dict]:
    query = select(RankingConfig).order_by(RankingConfig.name)
    if role:
        query = query.where(RankingConfig.role == role)
    return [
        {
            "id": config.id,
            "name": config.name,
            "role": config.role,
            "configuration": config.configuration_json,
        }
        for config in session.scalars(query)
    ]


@router.post(
    "/ranking-configs",
    response_model=RankingConfigResponse,
    status_code=201,
)
def create_ranking_config(
    payload: RankingConfigCreate,
    session: DatabaseSession,
) -> dict:
    if not payload.name.strip():
        raise HTTPException(422, "Il nome configurazione non può essere vuoto")
    config = RankingConfig(
        name=payload.name.strip(),
        role=payload.configuration.role,
        configuration_json=payload.configuration.model_dump(),
    )
    session.add(config)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(409, "Nome configurazione già esistente") from error
    session.refresh(config)
    return {
        "id": config.id,
        "name": config.name,
        "role": config.role,
        "configuration": config.configuration_json,
    }


@router.put(
    "/ranking-configs/{config_id}",
    response_model=RankingConfigResponse,
)
def update_ranking_config(
    config_id: int,
    payload: RankingConfigCreate,
    session: DatabaseSession,
) -> dict:
    if not payload.name.strip():
        raise HTTPException(422, "Il nome configurazione non può essere vuoto")
    config = session.get(RankingConfig, config_id)
    if config is None:
        raise HTTPException(404, "Configurazione ranking non trovata")
    config.name = payload.name.strip()
    config.role = payload.configuration.role
    config.configuration_json = payload.configuration.model_dump()
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(409, "Nome configurazione già esistente") from error
    return {
        "id": config.id,
        "name": config.name,
        "role": config.role,
        "configuration": config.configuration_json,
    }


@router.delete("/ranking-configs/{config_id}", status_code=204)
def delete_ranking_config(config_id: int, session: DatabaseSession) -> None:
    config = session.get(RankingConfig, config_id)
    if config is None:
        raise HTTPException(404, "Configurazione ranking non trovata")
    session.delete(config)
    session.commit()


@router.get("/players", response_model=PlayerPage)
def get_players(
    session: DatabaseSession,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    role: Annotated[Literal["P", "D", "C", "A"] | None, Query()] = None,
    team: Annotated[str | None, Query(min_length=1, max_length=150)] = None,
    min_appearances: Annotated[int | None, Query(ge=0, le=38)] = None,
    min_seasons: Annotated[int | None, Query(ge=1, le=4)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort_by: Annotated[
        Literal[
            "name",
            "latest_season",
            "appearances",
            "fantasy_average",
            "average_rating",
        ],
        Query(),
    ] = "name",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "asc",
) -> dict:
    return list_players(
        session,
        search=search,
        role=role,
        team=team,
        min_appearances=min_appearances,
        min_seasons=min_seasons,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/current-list", response_model=CurrentListPage)
def get_current_list(
    session: DatabaseSession,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    role: Annotated[Literal["P", "D", "C", "A"] | None, Query()] = None,
    team: Annotated[str | None, Query(min_length=1, max_length=150)] = None,
    mapping_status: Annotated[
        Literal["certain_external_id", "new_player"] | None, Query()
    ] = None,
    min_quotation: Annotated[float | None, Query(ge=0)] = None,
    max_quotation: Annotated[float | None, Query(ge=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort_by: Annotated[
        Literal["name", "team", "quotation", "mantra_quotation", "fvm", "fvm_mantra"],
        Query(),
    ] = "quotation",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "desc",
) -> dict:
    if min_quotation is not None and max_quotation is not None and min_quotation > max_quotation:
        raise HTTPException(422, "La quotazione minima non può superare la massima")
    return list_current_players(
        session,
        search=search,
        role=role,
        team=team,
        mapping_status=mapping_status,
        min_quotation=min_quotation,
        max_quotation=max_quotation,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/players/compare", response_model=CompareResponse)
def compare_players(
    session: DatabaseSession,
    ids: Annotated[list[int], Query(min_length=2, max_length=10)],
) -> dict:
    unique_ids = list(dict.fromkeys(ids))
    if len(unique_ids) < 2:
        raise HTTPException(422, "Sono richiesti almeno due ID distinti")
    players = []
    missing = []
    for player_id in unique_ids:
        detail = player_detail(session, player_id)
        if detail is None:
            missing.append(player_id)
        else:
            players.append(detail)
    if missing:
        raise HTTPException(404, f"Giocatori non trovati: {missing}")
    return {"players": players}


@router.get("/players/{player_id}", response_model=PlayerDetailResponse)
def get_player(player_id: int, session: DatabaseSession) -> dict:
    detail = player_detail(session, player_id)
    if detail is None:
        raise HTTPException(404, "Giocatore non trovato")
    return detail


@router.get(
    "/players/{player_id}/history",
    response_model=list[PlayerHistoryItem],
)
def get_player_history(player_id: int, session: DatabaseSession) -> list[dict]:
    if session.get(Player, player_id) is None:
        raise HTTPException(404, "Giocatore non trovato")
    return player_history(session, player_id)


@router.get(
    "/data-quality/issues",
    response_model=list[DataQualityIssueResponse],
)
def get_data_quality_issues(
    session: DatabaseSession,
    status: Annotated[Literal["warning", "pending", "all"], Query()] = "all",
) -> list[dict]:
    issues: list[dict] = []
    if status in ("warning", "all"):
        warning_rows = session.execute(
            select(SourceRecord, SourceImport, Season)
            .join(SourceImport, SourceImport.id == SourceRecord.import_id)
            .outerjoin(Season, Season.id == SourceImport.season_id)
            .where(SourceRecord.validation_status == "warning")
        ).all()
        for record, source_import, season in warning_rows:
            issues.append(
                {
                    "category": "data_quality",
                    "issue_id": record.id,
                    "status": record.validation_status,
                    "player_name": record.raw_payload_json.get("Nome"),
                    "season": season.code if season else None,
                    "message": "Record importato con warning di qualità",
                    "source_row_number": record.source_row_number,
                }
            )
    if status in ("pending", "all"):
        reviews = list(
            session.scalars(
                select(PlayerMappingReview).where(
                    PlayerMappingReview.status == "pending"
                )
            )
        )
        for review in reviews:
            source = session.get(SourceRecord, review.source_record_id)
            source_import = (
                session.get(SourceImport, source.import_id) if source else None
            )
            season = (
                session.get(Season, source_import.season_id)
                if source_import and source_import.season_id
                else None
            )
            issues.append(
                {
                    "category": "player_mapping",
                    "issue_id": review.id,
                    "status": review.status,
                    "player_name": (
                        source.raw_payload_json.get("Nome") if source else None
                    ),
                    "season": season.code if season else None,
                    "message": review.reason,
                    "source_row_number": (
                        source.source_row_number if source else None
                    ),
                }
            )
    return issues


@router.get(
    "/player-mappings/pending",
    response_model=list[PendingMappingResponse],
)
def get_pending_mappings(session: DatabaseSession) -> list[dict]:
    reviews = list(
        session.scalars(
            select(PlayerMappingReview)
            .where(PlayerMappingReview.status == "pending")
            .order_by(PlayerMappingReview.id)
        )
    )
    result = []
    for review in reviews:
        source = session.get(SourceRecord, review.source_record_id)
        source_import = session.get(SourceImport, source.import_id) if source else None
        season = (
            session.get(Season, source_import.season_id)
            if source_import and source_import.season_id
            else None
        )
        candidate = (
            session.get(Player, review.candidate_player_id)
            if review.candidate_player_id
            else None
        )
        source_player = (
            session.scalar(
                select(Player).where(
                    Player.external_provider == "fantacalcio",
                    Player.external_player_id == source.external_player_id,
                )
            )
            if source
            else None
        )
        candidate_history = (
            player_history(session, candidate.id) if candidate else []
        )
        raw = source.raw_payload_json if source else {}
        result.append(
            {
                "id": review.id,
                "source_record_id": review.source_record_id,
                "source_external_player_id": (
                    source.external_player_id if source else None
                ),
                "source_name": (
                    source.raw_payload_json.get("Nome") if source else None
                ),
                "season": season.code if season else None,
                "reason": review.reason,
                "notes": review.notes,
                "source_player_id": source_player.id if source_player else None,
                "source_role": raw.get("R"),
                "source_team": raw.get("Squadra"),
                "source_rated_appearances": raw.get("Pv"),
                "candidate": {
                    "player_id": candidate.id if candidate else None,
                    "display_name": candidate.display_name if candidate else None,
                    "similarity_score": review.similarity_score,
                    "roles": sorted(
                        {item["role"] for item in candidate_history}
                    ),
                    "teams": sorted(
                        {
                            team
                            for item in candidate_history
                            for team in item["teams"]
                        }
                    ),
                    "seasons": [item["season"] for item in candidate_history],
                },
            }
        )
    return result


@router.get("/player-mappings/{review_id}/merge-preview")
def get_merge_preview(review_id: int, session: DatabaseSession) -> dict:
    try:
        return merge_preview(session, review_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@router.post(
    "/player-mappings/{review_id}/merge",
    response_model=MergeAuditResponse,
)
def post_merge(
    review_id: int,
    payload: ApplyMergeRequest,
    session: DatabaseSession,
) -> dict:
    try:
        audit = apply_merge(
            session,
            review_id,
            payload.preview_token,
            notes=payload.notes,
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return {
        "id": audit.id,
        "review_id": audit.review_id,
        "source_player_id": audit.source_player_id,
        "target_player_id": audit.target_player_id,
        "status": audit.status,
        "backup_path": audit.backup_path,
    }


@router.post(
    "/player-merges/{audit_id}/revert",
    response_model=MergeAuditResponse,
)
def post_revert_merge(audit_id: int, session: DatabaseSession) -> dict:
    try:
        audit = revert_merge(session, audit_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return {
        "id": audit.id,
        "review_id": audit.review_id,
        "source_player_id": audit.source_player_id,
        "target_player_id": audit.target_player_id,
        "status": audit.status,
        "backup_path": audit.backup_path,
    }


@router.post(
    "/player-mappings/{review_id}/resolve",
    response_model=ResolveMappingResponse,
)
def resolve_mapping(
    review_id: int,
    payload: ResolveMappingRequest,
    session: DatabaseSession,
) -> dict:
    review = session.get(PlayerMappingReview, review_id)
    if review is None:
        raise HTTPException(404, "Revisione non trovata")
    if review.status != "pending":
        raise HTTPException(409, "Revisione già risolta")

    resolved_player_id = payload.resolved_player_id
    if payload.resolution == "confirm_candidate":
        resolved_player_id = resolved_player_id or review.candidate_player_id
        if resolved_player_id is None or session.get(Player, resolved_player_id) is None:
            raise HTTPException(422, "È richiesto un giocatore candidato valido")
    elif payload.resolution == "new_player":
        source = session.get(SourceRecord, review.source_record_id)
        if source is None:
            raise HTTPException(409, "Record sorgente non disponibile")
        source_player = session.scalar(
            select(Player).where(
                Player.external_provider == "fantacalcio",
                Player.external_player_id == source.external_player_id,
            )
        )
        if source_player is None:
            raise HTTPException(409, "Identità sorgente non disponibile")
        resolved_player_id = source_player.id
    else:
        resolved_player_id = None

    review.status = "excluded" if payload.resolution == "exclude" else "resolved"
    review.resolution = payload.resolution
    review.resolved_player_id = resolved_player_id
    review.resolved_by = "local-user"
    review.resolved_at = datetime.now(timezone.utc)
    review.notes = payload.notes or review.notes
    session.commit()
    return {
        "id": review.id,
        "status": review.status,
        "resolution": review.resolution,
        "resolved_player_id": review.resolved_player_id,
    }
