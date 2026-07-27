"""Motore puro per ranking configurabili basati su percentili."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


METRIC_DIRECTIONS: dict[str, str] = {
    "fantasy_average_recency_weighted": "higher",
    "average_rating_recency_weighted": "higher",
    "goals_per_appearance": "higher",
    "goals_conceded_per_appearance": "lower",
    "penalties_saved_per_appearance": "higher",
    "assists_per_appearance": "higher",
    "bonus_events_per_appearance": "higher",
    "malus_events_per_appearance": "lower",
    "continuity": "higher",
    "fantasy_average_volatility": "lower",
    "latest_fantasy_average": "higher",
    "reliability_score": "higher",
}
METRIC_ROLES: dict[str, tuple[str, ...]] = {
    "goals_conceded_per_appearance": ("P",),
    "penalties_saved_per_appearance": ("P",),
}


@dataclass(frozen=True)
class RankingCandidate:
    player_id: int
    display_name: str
    metrics: Mapping[str, float | int | None]


def _percentiles(
    values: Mapping[int, float],
    *,
    direction: str,
) -> dict[int, float]:
    """Assegna percentili 0-100, usando la posizione media per i pareggi."""

    ordered = sorted(values.items(), key=lambda item: item[1])
    result: dict[int, float] = {}
    count = len(ordered)
    index = 0
    while index < count:
        end = index + 1
        while end < count and ordered[end][1] == ordered[index][1]:
            end += 1
        average_position = (index + end - 1) / 2
        percentile = 100.0 if count == 1 else average_position / (count - 1) * 100
        if direction == "lower":
            percentile = 100 - percentile
        for tied_index in range(index, end):
            result[ordered[tied_index][0]] = percentile
        index = end
    return result


def calculate_ranking(
    candidates: Sequence[RankingCandidate],
    weights: Mapping[str, float],
) -> dict:
    unknown = set(weights) - set(METRIC_DIRECTIONS)
    if unknown:
        raise ValueError(f"Metriche non supportate: {sorted(unknown)}")
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("I pesi non possono essere negativi")
    if any(not math.isfinite(weight) or weight > 1000 for weight in weights.values()):
        raise ValueError("I pesi devono essere finiti e non superiori a 1000")
    active = {metric: weight for metric, weight in weights.items() if weight > 0}
    if not active:
        raise ValueError("È richiesto almeno un peso maggiore di zero")

    eligible: list[RankingCandidate] = []
    excluded: list[dict] = []
    for candidate in candidates:
        missing = [
            metric
            for metric in active
            if candidate.metrics.get(metric) is None
        ]
        if missing:
            excluded.append(
                {
                    "player_id": candidate.player_id,
                    "display_name": candidate.display_name,
                    "missing_metrics": missing,
                }
            )
        else:
            eligible.append(candidate)

    percentiles = {
        metric: _percentiles(
            {
                candidate.player_id: float(candidate.metrics[metric])  # type: ignore[arg-type]
                for candidate in eligible
            },
            direction=METRIC_DIRECTIONS[metric],
        )
        for metric in active
    }
    weight_total = sum(active.values())
    rows = []
    for candidate in eligible:
        components = {}
        score = 0.0
        for metric, weight in active.items():
            percentile = percentiles[metric][candidate.player_id]
            contribution = percentile * weight / weight_total
            score += contribution
            components[metric] = {
                "value": float(candidate.metrics[metric]),  # type: ignore[arg-type]
                "percentile": percentile,
                "weight": weight,
                "contribution": contribution,
                "direction": METRIC_DIRECTIONS[metric],
            }
        rows.append(
            {
                "player_id": candidate.player_id,
                "display_name": candidate.display_name,
                "score": score,
                "metrics": components,
                "reliability_score": candidate.metrics.get("reliability_score"),
                "total_pv": candidate.metrics.get("total_pv"),
            }
        )
    rows.sort(key=lambda row: (-row["score"], row["display_name"], row["player_id"]))
    for position, row in enumerate(rows, start=1):
        row["position"] = position
    return {
        "initial_pool_size": len(candidates),
        "eligible_pool_size": len(eligible),
        "excluded": excluded,
        "items": rows,
    }
