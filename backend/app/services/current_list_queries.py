"""Query del listone corrente, separate dalle statistiche storiche."""

from __future__ import annotations

import math

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from backend.app.models import CurrentSeasonList, Player, PlayerSeasonStats, Season, Team


SORT_COLUMNS = {
    "name": CurrentSeasonList.source_name,
    "team": Team.display_name,
    "quotation": CurrentSeasonList.quotation,
    "mantra_quotation": CurrentSeasonList.mantra_quotation,
    "fvm": CurrentSeasonList.fvm,
    "fvm_mantra": CurrentSeasonList.fvm_mantra,
}


def list_current_players(
    session: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    team: str | None = None,
    mapping_status: str | None = None,
    min_quotation: float | None = None,
    max_quotation: float | None = None,
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "quotation",
    sort_order: str = "desc",
) -> dict:
    history = (
        select(
            PlayerSeasonStats.player_id.label("player_id"),
            func.count(PlayerSeasonStats.id).label("historical_seasons"),
        )
        .join(Season, Season.id == PlayerSeasonStats.season_id)
        .where(Season.is_current.is_(False))
        .group_by(PlayerSeasonStats.player_id)
        .subquery()
    )
    query = (
        select(CurrentSeasonList, Player, Team, history.c.historical_seasons)
        .join(Player, Player.id == CurrentSeasonList.player_id)
        .join(Team, Team.id == CurrentSeasonList.official_team_id)
        .join(Season, Season.id == CurrentSeasonList.season_id)
        .outerjoin(history, history.c.player_id == Player.id)
        .where(Season.is_current.is_(True))
    )
    if search:
        query = query.where(CurrentSeasonList.source_name.ilike(f"%{search.strip()}%"))
    if role:
        query = query.where(CurrentSeasonList.official_classic_role == role)
    if team:
        query = query.where(func.lower(Team.display_name) == team.strip().lower())
    if mapping_status:
        query = query.where(CurrentSeasonList.mapping_status == mapping_status)
    if min_quotation is not None:
        query = query.where(CurrentSeasonList.quotation >= min_quotation)
    if max_quotation is not None:
        query = query.where(CurrentSeasonList.quotation <= max_quotation)

    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total_items = session.scalar(count_query) or 0
    column = SORT_COLUMNS[sort_by]
    ordering = desc(column) if sort_order == "desc" else asc(column)
    rows = session.execute(
        query.order_by(ordering, asc(CurrentSeasonList.source_name), asc(CurrentSeasonList.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "player_id": player.id,
                "external_player_id": item.external_player_id,
                "name": item.source_name,
                "classic_role": item.official_classic_role,
                "mantra_roles": item.official_mantra_roles.split(";") if item.official_mantra_roles else [],
                "team": current_team.display_name,
                "quotation": item.quotation,
                "initial_quotation": item.initial_quotation,
                "quotation_change": (
                    item.quotation - item.initial_quotation
                    if item.quotation is not None and item.initial_quotation is not None
                    else None
                ),
                "mantra_quotation": item.mantra_quotation,
                "initial_mantra_quotation": item.initial_mantra_quotation,
                "mantra_quotation_change": (
                    item.mantra_quotation - item.initial_mantra_quotation
                    if item.mantra_quotation is not None and item.initial_mantra_quotation is not None
                    else None
                ),
                "fvm": item.fvm,
                "fvm_mantra": item.fvm_mantra,
                "mapping_status": item.mapping_status,
                "historical_seasons": int(historical_seasons or 0),
            }
            for item, player, current_team, historical_seasons in rows
        ],
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": math.ceil(total_items / page_size) if total_items else 0,
    }
