from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from backend.analytics.player_metrics import (
    SeasonPerformance,
    calculate_player_metrics,
    metrics_dict,
)
from backend.analytics.ranking import (
    METRIC_ROLES,
    RankingCandidate,
    calculate_ranking,
)
from backend.app.models import (
    Player,
    PlayerAlias,
    PlayerSeasonStats,
    PlayerTeamSeason,
    Season,
    Team,
)


def player_history(session: Session, player_id: int) -> list[dict[str, Any]]:
    rows = session.execute(
        select(PlayerSeasonStats, Season)
        .join(Season, Season.id == PlayerSeasonStats.season_id)
        .where(PlayerSeasonStats.player_id == player_id)
        .order_by(Season.start_year)
    ).all()
    history = []
    for stats, season in rows:
        teams = list(
            session.scalars(
                select(Team.display_name)
                .join(PlayerTeamSeason, PlayerTeamSeason.team_id == Team.id)
                .where(
                    PlayerTeamSeason.player_season_stats_id == stats.id
                )
                .order_by(Team.display_name)
            )
        )
        history.append(
            {
                "season_id": season.id,
                "season": season.code,
                "role": stats.classic_role,
                "mantra_roles": stats.mantra_roles.split(";"),
                "teams": teams,
                "rated_appearances": stats.rated_appearances,
                "average_rating": stats.average_rating,
                "fantasy_average": stats.fantasy_average,
                "goals_scored": stats.goals_scored,
                "goals_conceded": stats.goals_conceded,
                "penalties_saved": stats.penalties_saved,
                "penalties_taken": stats.penalties_taken,
                "penalties_scored": stats.penalties_scored,
                "penalties_missed": stats.penalties_missed,
                "assists": stats.assists,
                "yellow_cards": stats.yellow_cards,
                "red_cards": stats.red_cards,
                "own_goals": stats.own_goals,
                "quality_status": stats.quality_status,
                "quality_notes": stats.quality_notes,
            }
        )
    return history


def player_metrics(
    session: Session,
    player_id: int,
    *,
    selected_seasons: Sequence[str] | None = None,
    decay: float = 0.75,
    continuity_threshold: int = 19,
) -> dict[str, Any]:
    seasons = list(
        session.scalars(select(Season).order_by(Season.start_year))
    )
    season_codes = (
        list(selected_seasons) if selected_seasons else [season.code for season in seasons]
    )
    rows = session.execute(
        select(PlayerSeasonStats, Season)
        .join(Season, Season.id == PlayerSeasonStats.season_id)
        .where(PlayerSeasonStats.player_id == player_id)
        .order_by(Season.start_year)
    ).all()
    return _metrics_from_rows(
        rows,
        season_codes,
        decay=decay,
        continuity_threshold=continuity_threshold,
    )


def _metrics_from_rows(
    rows: Sequence[tuple[PlayerSeasonStats, Season]],
    season_codes: Sequence[str],
    *,
    decay: float,
    continuity_threshold: int,
) -> dict[str, Any]:
    performances = [
        SeasonPerformance(
            season=season.code,
            role=stats.classic_role,
            rated_appearances=stats.rated_appearances,
            average_rating=stats.average_rating,
            fantasy_average=stats.fantasy_average,
            goals_scored=stats.goals_scored,
            goals_conceded=stats.goals_conceded,
            penalties_saved=stats.penalties_saved,
            penalties_missed=stats.penalties_missed,
            assists=stats.assists,
            yellow_cards=stats.yellow_cards,
            red_cards=stats.red_cards,
            own_goals=stats.own_goals,
        )
        for stats, season in rows
    ]
    return metrics_dict(
        calculate_player_metrics(
            performances,
            season_codes,
            decay=decay,
            continuity_threshold=continuity_threshold,
        )
    )


def calculate_players_ranking(
    session: Session,
    *,
    role: str,
    selected_seasons: Sequence[str],
    minimum_appearances: int,
    recency_decay: float,
    continuity_threshold: int,
    metric_weights: dict[str, float],
) -> dict[str, Any]:
    disallowed = [
        metric
        for metric, weight in metric_weights.items()
        if weight > 0 and metric in METRIC_ROLES and role not in METRIC_ROLES[metric]
    ]
    if disallowed:
        raise ValueError(
            f"Metriche non disponibili per il ruolo {role}: {sorted(disallowed)}"
        )
    if len(set(selected_seasons)) != len(selected_seasons):
        raise ValueError("Le stagioni selezionate non possono essere duplicate")
    known_seasons = set(session.scalars(select(Season.code)))
    unknown_seasons = set(selected_seasons) - known_seasons
    if unknown_seasons:
        raise ValueError(f"Stagioni non disponibili: {sorted(unknown_seasons)}")

    grouped: dict[int, list[tuple[PlayerSeasonStats, Season]]] = defaultdict(list)
    players: dict[int, Player] = {}
    rows = session.execute(
        select(Player, PlayerSeasonStats, Season)
        .join(PlayerSeasonStats, PlayerSeasonStats.player_id == Player.id)
        .join(Season, Season.id == PlayerSeasonStats.season_id)
        .where(Season.code.in_(selected_seasons))
        .order_by(Player.id, Season.start_year)
    ).all()
    for player, stats, season in rows:
        players[player.id] = player
        grouped[player.id].append((stats, season))

    candidates = []
    for player_id, metric_rows in grouped.items():
        player = players[player_id]
        metrics = _metrics_from_rows(
            metric_rows,
            selected_seasons,
            decay=recency_decay,
            continuity_threshold=continuity_threshold,
        )
        if metrics["latest_role"] != role:
            continue
        if metrics["total_pv"] < minimum_appearances:
            continue
        candidates.append(
            RankingCandidate(
                player_id=player.id,
                display_name=player.display_name,
                metrics=metrics,
            )
        )
    result = calculate_ranking(candidates, metric_weights)
    result["configuration"] = {
        "role": role,
        "selected_seasons": list(selected_seasons),
        "minimum_appearances": minimum_appearances,
        "recency_decay": recency_decay,
        "continuity_threshold": continuity_threshold,
        "metric_weights": metric_weights,
    }
    return result


def player_detail(session: Session, player_id: int) -> dict[str, Any] | None:
    player = session.get(Player, player_id)
    if player is None:
        return None
    aliases = list(
        session.scalars(
            select(PlayerAlias.source_name)
            .where(PlayerAlias.player_id == player_id)
            .order_by(PlayerAlias.source_name)
        )
    )
    return {
        "id": player.id,
        "display_name": player.display_name,
        "normalized_name": player.normalized_name,
        "external_provider": player.external_provider,
        "external_player_id": player.external_player_id,
        "matching_status": player.matching_status,
        "manual_notes": player.manual_notes,
        "aliases": aliases,
        "history": player_history(session, player_id),
        "metrics": player_metrics(session, player_id),
    }


def list_players(
    session: Session,
    *,
    search: str | None,
    role: str | None,
    team: str | None,
    min_appearances: int | None,
    min_seasons: int | None,
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
) -> dict[str, Any]:
    stats_for_latest = aliased(PlayerSeasonStats)
    season_for_latest = aliased(Season)
    latest_year = (
        select(
            PlayerSeasonStats.player_id.label("player_id"),
            func.max(Season.start_year).label("latest_year"),
        )
        .join(Season, Season.id == PlayerSeasonStats.season_id)
        .group_by(PlayerSeasonStats.player_id)
        .subquery()
    )
    season_count = (
        select(func.count(PlayerSeasonStats.id))
        .where(PlayerSeasonStats.player_id == Player.id)
        .correlate(Player)
        .scalar_subquery()
    )
    latest_team = (
        select(Team.display_name)
        .join(PlayerTeamSeason, PlayerTeamSeason.team_id == Team.id)
        .where(
            PlayerTeamSeason.player_season_stats_id == stats_for_latest.id
        )
        .limit(1)
        .correlate(stats_for_latest)
        .scalar_subquery()
    )
    query = (
        select(
            Player,
            stats_for_latest,
            season_for_latest,
            season_count.label("available_seasons"),
            latest_team.label("latest_team"),
        )
        .join(latest_year, latest_year.c.player_id == Player.id)
        .join(
            season_for_latest,
            season_for_latest.start_year == latest_year.c.latest_year,
        )
        .join(
            stats_for_latest,
            (stats_for_latest.player_id == Player.id)
            & (stats_for_latest.season_id == season_for_latest.id),
        )
    )
    if search:
        query = query.where(Player.normalized_name.contains(search.casefold()))
    if role:
        query = query.where(stats_for_latest.classic_role == role)
    if team:
        query = query.where(latest_team == team)
    if min_appearances is not None:
        query = query.where(stats_for_latest.rated_appearances >= min_appearances)
    if min_seasons is not None:
        query = query.where(season_count >= min_seasons)

    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = session.scalar(count_query) or 0
    sort_columns = {
        "name": Player.display_name,
        "latest_season": season_for_latest.start_year,
        "appearances": stats_for_latest.rated_appearances,
        "fantasy_average": stats_for_latest.fantasy_average,
        "average_rating": stats_for_latest.average_rating,
    }
    sort_column = sort_columns[sort_by]
    ordering = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    rows = session.execute(
        query.order_by(ordering, Player.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for player, stats, season, available_seasons, team_name in rows:
        metrics = player_metrics(session, player.id)
        items.append(
            {
                "id": player.id,
                "display_name": player.display_name,
                "external_player_id": player.external_player_id,
                "latest_season": season.code,
                "latest_role": stats.classic_role,
                "latest_team": team_name,
                "latest_rated_appearances": stats.rated_appearances,
                "available_seasons": available_seasons,
                "reliability_score": metrics["reliability_score"],
                "reliability_band": metrics["reliability_band"],
            }
        )
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }
