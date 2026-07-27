"""Calcolo puro e trasparente delle metriche storiche approvate."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SeasonPerformance:
    season: str
    role: str
    rated_appearances: int
    average_rating: float | None
    fantasy_average: float | None
    goals_scored: int
    goals_conceded: int
    penalties_saved: int
    penalties_missed: int
    assists: int
    yellow_cards: int
    red_cards: int
    own_goals: int


@dataclass(frozen=True)
class PlayerMetrics:
    total_pv: int
    available_seasons: int
    selected_seasons: int
    seasons_with_pv: int
    latest_calendar_season: str
    latest_calendar_season_present: bool
    latest_calendar_season_pv: int
    latest_available_season: str | None
    latest_role: str | None
    average_rating_simple: float | None
    average_rating_weighted: float | None
    fantasy_average_simple: float | None
    fantasy_average_weighted: float | None
    latest_average_rating: float | None
    latest_fantasy_average: float | None
    latest_two_average_rating_simple: float | None
    latest_two_average_rating_weighted: float | None
    latest_two_fantasy_average_simple: float | None
    latest_two_fantasy_average_weighted: float | None
    average_rating_recency_weighted: float | None
    fantasy_average_recency_weighted: float | None
    fantasy_average_absolute_change: float | None
    fantasy_average_percentage_change: float | None
    average_rating_trend_slope: float | None
    fantasy_average_trend_slope: float | None
    goals_per_appearance: float | None
    goals_conceded_per_appearance: float | None
    penalties_saved_per_appearance: float | None
    assists_per_appearance: float | None
    bonus_events_per_appearance: float | None
    malus_events_per_appearance: float | None
    fm_mv_delta: float | None
    fm_mv_ratio: float | None
    continuity: float
    fantasy_average_volatility: float | None
    sample_component: float
    coverage_component: float
    recent_component: float
    reliability_score: float
    reliability_band: str
    shrinkage_weight: float
    fantasy_average_shrunk: float | None


def _simple(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _weighted(
    records: Sequence[SeasonPerformance],
    field: str,
    *,
    extra_weights: Mapping[str, float] | None = None,
) -> float | None:
    numerator = denominator = 0.0
    for record in records:
        value = getattr(record, field)
        if value is None or record.rated_appearances <= 0:
            continue
        extra = extra_weights.get(record.season, 1.0) if extra_weights else 1.0
        weight = record.rated_appearances * extra
        numerator += float(value) * weight
        denominator += weight
    return numerator / denominator if denominator else None


def _change(
    records: Sequence[SeasonPerformance],
    field: str,
) -> tuple[float | None, float | None]:
    valid = [record for record in records if getattr(record, field) is not None]
    if len(valid) < 2:
        return None, None
    previous = float(getattr(valid[-2], field))
    latest = float(getattr(valid[-1], field))
    absolute = latest - previous
    percentage = absolute / abs(previous) * 100 if previous != 0 else None
    return absolute, percentage


def _volatility(
    records: Sequence[SeasonPerformance],
    field: str,
) -> float | None:
    valid = [
        record
        for record in records
        if getattr(record, field) is not None and record.rated_appearances > 0
    ]
    if len(valid) < 2:
        return None
    mean = _weighted(valid, field)
    if mean is None:
        return None
    denominator = sum(record.rated_appearances for record in valid)
    variance = sum(
        record.rated_appearances * (float(getattr(record, field)) - mean) ** 2
        for record in valid
    ) / denominator
    return math.sqrt(variance)


def _weighted_trend_slope(
    records: Sequence[SeasonPerformance],
    field: str,
    season_position: Mapping[str, int],
) -> float | None:
    valid = [
        record
        for record in records
        if getattr(record, field) is not None and record.rated_appearances > 0
    ]
    if len(valid) < 2:
        return None
    weight_total = sum(record.rated_appearances for record in valid)
    mean_x = sum(
        season_position[record.season] * record.rated_appearances
        for record in valid
    ) / weight_total
    mean_y = sum(
        float(getattr(record, field)) * record.rated_appearances
        for record in valid
    ) / weight_total
    numerator = sum(
        record.rated_appearances
        * (season_position[record.season] - mean_x)
        * (float(getattr(record, field)) - mean_y)
        for record in valid
    )
    denominator = sum(
        record.rated_appearances
        * (season_position[record.season] - mean_x) ** 2
        for record in valid
    )
    return numerator / denominator if denominator else None


def _band(score: float) -> str:
    if score < 40:
        return "low"
    if score < 70:
        return "medium"
    return "high"


def calculate_player_metrics(
    records: Sequence[SeasonPerformance],
    selected_seasons: Sequence[str],
    *,
    decay: float = 0.75,
    continuity_threshold: int = 19,
    shrinkage_k: float = 20,
    role_mean_fantasy_average: float | None = None,
) -> PlayerMetrics:
    """Calcola le metriche approvate sulle stagioni selezionate."""

    if not selected_seasons:
        raise ValueError("È richiesta almeno una stagione selezionata")
    if not 0 < decay <= 1:
        raise ValueError("decay deve essere compreso tra 0 escluso e 1")
    if continuity_threshold < 0:
        raise ValueError("continuity_threshold non può essere negativo")
    if shrinkage_k <= 0:
        raise ValueError("shrinkage_k deve essere positivo")

    season_position = {season: index for index, season in enumerate(selected_seasons)}
    selected = sorted(
        [record for record in records if record.season in season_position],
        key=lambda record: season_position[record.season],
    )
    if len({record.season for record in selected}) != len(selected):
        raise ValueError("Più record dello stesso giocatore nella stessa stagione")

    latest_calendar = selected_seasons[-1]
    by_season = {record.season: record for record in selected}
    latest_calendar_record = by_season.get(latest_calendar)
    positive = [record for record in selected if record.rated_appearances > 0]
    latest_available = selected[-1] if selected else None
    latest_with_rating = positive[-1] if positive else None
    latest_two = positive[-2:]
    total_pv = sum(record.rated_appearances for record in selected)

    recency_weights = {
        season: decay ** (len(selected_seasons) - 1 - index)
        for index, season in enumerate(selected_seasons)
    }
    fantasy_weighted = _weighted(selected, "fantasy_average")
    rating_weighted = _weighted(selected, "average_rating")
    absolute_change, percentage_change = _change(selected, "fantasy_average")

    goals = sum(record.goals_scored for record in selected)
    assists = sum(record.assists for record in selected)
    bonus_events = sum(
        record.goals_scored + record.assists + record.penalties_saved
        for record in selected
    )
    malus_events = sum(
        record.yellow_cards
        + record.red_cards
        + record.own_goals
        + record.penalties_missed
        + record.goals_conceded
        for record in selected
    )

    available_seasons = len(selected)
    selected_count = len(selected_seasons)
    continuity_hits = sum(
        by_season.get(season) is not None
        and by_season[season].rated_appearances >= continuity_threshold
        for season in selected_seasons
    )
    sample_component = min(total_pv / 76, 1)
    coverage_component = available_seasons / selected_count
    latest_calendar_pv = (
        latest_calendar_record.rated_appearances
        if latest_calendar_record is not None
        else 0
    )
    recent_component = min(latest_calendar_pv / 19, 1)
    reliability = 100 * (
        0.50 * sample_component
        + 0.25 * coverage_component
        + 0.25 * recent_component
    )

    shrinkage_weight = total_pv / (total_pv + shrinkage_k)
    shrunk = (
        shrinkage_weight * fantasy_weighted
        + (1 - shrinkage_weight) * role_mean_fantasy_average
        if fantasy_weighted is not None and role_mean_fantasy_average is not None
        else None
    )
    fm_mv_delta = (
        fantasy_weighted - rating_weighted
        if fantasy_weighted is not None and rating_weighted is not None
        else None
    )
    fm_mv_ratio = (
        fantasy_weighted / rating_weighted
        if fantasy_weighted is not None
        and rating_weighted is not None
        and rating_weighted != 0
        else None
    )

    return PlayerMetrics(
        total_pv=total_pv,
        available_seasons=available_seasons,
        selected_seasons=selected_count,
        seasons_with_pv=len(positive),
        latest_calendar_season=latest_calendar,
        latest_calendar_season_present=latest_calendar_record is not None,
        latest_calendar_season_pv=latest_calendar_pv,
        latest_available_season=(
            latest_available.season if latest_available is not None else None
        ),
        latest_role=latest_available.role if latest_available is not None else None,
        average_rating_simple=_simple(
            [record.average_rating for record in selected]
        ),
        average_rating_weighted=rating_weighted,
        fantasy_average_simple=_simple(
            [record.fantasy_average for record in selected]
        ),
        fantasy_average_weighted=fantasy_weighted,
        latest_average_rating=(
            latest_with_rating.average_rating
            if latest_with_rating is not None
            else None
        ),
        latest_fantasy_average=(
            latest_with_rating.fantasy_average
            if latest_with_rating is not None
            else None
        ),
        latest_two_average_rating_simple=_simple(
            [record.average_rating for record in latest_two]
        ),
        latest_two_average_rating_weighted=_weighted(
            latest_two, "average_rating"
        ),
        latest_two_fantasy_average_simple=_simple(
            [record.fantasy_average for record in latest_two]
        ),
        latest_two_fantasy_average_weighted=_weighted(
            latest_two, "fantasy_average"
        ),
        average_rating_recency_weighted=_weighted(
            selected,
            "average_rating",
            extra_weights=recency_weights,
        ),
        fantasy_average_recency_weighted=_weighted(
            selected,
            "fantasy_average",
            extra_weights=recency_weights,
        ),
        fantasy_average_absolute_change=absolute_change,
        fantasy_average_percentage_change=percentage_change,
        average_rating_trend_slope=_weighted_trend_slope(
            selected, "average_rating", season_position
        ),
        fantasy_average_trend_slope=_weighted_trend_slope(
            selected, "fantasy_average", season_position
        ),
        goals_per_appearance=goals / total_pv if total_pv else None,
        goals_conceded_per_appearance=(
            sum(record.goals_conceded for record in selected) / total_pv
            if total_pv
            else None
        ),
        penalties_saved_per_appearance=(
            sum(record.penalties_saved for record in selected) / total_pv
            if total_pv
            else None
        ),
        assists_per_appearance=assists / total_pv if total_pv else None,
        bonus_events_per_appearance=bonus_events / total_pv if total_pv else None,
        malus_events_per_appearance=malus_events / total_pv if total_pv else None,
        fm_mv_delta=fm_mv_delta,
        fm_mv_ratio=fm_mv_ratio,
        continuity=continuity_hits / selected_count,
        fantasy_average_volatility=_volatility(selected, "fantasy_average"),
        sample_component=sample_component,
        coverage_component=coverage_component,
        recent_component=recent_component,
        reliability_score=reliability,
        reliability_band=_band(reliability),
        shrinkage_weight=shrinkage_weight,
        fantasy_average_shrunk=shrunk,
    )


def metrics_dict(metrics: PlayerMetrics) -> dict[str, Any]:
    return asdict(metrics)
