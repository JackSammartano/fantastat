from __future__ import annotations

import pytest

from backend.analytics.ranking import RankingCandidate, calculate_ranking


def candidate(player_id: int, fm: float | None, volatility: float | None):
    return RankingCandidate(
        player_id=player_id,
        display_name=f"P{player_id}",
        metrics={
            "fantasy_average_recency_weighted": fm,
            "fantasy_average_volatility": volatility,
            "reliability_score": 50,
            "total_pv": 30,
        },
    )


def test_ranking_combines_percentiles_and_inverts_lower_is_better() -> None:
    result = calculate_ranking(
        [candidate(1, 8, 2), candidate(2, 7, 1), candidate(3, 6, 3)],
        {
            "fantasy_average_recency_weighted": 3,
            "fantasy_average_volatility": 1,
        },
    )
    assert [row["player_id"] for row in result["items"]] == [1, 2, 3]
    assert result["items"][0]["score"] == pytest.approx(87.5)
    assert result["items"][1]["score"] == pytest.approx(62.5)
    assert result["items"][0]["position"] == 1


def test_ties_receive_average_percentile() -> None:
    result = calculate_ranking(
        [candidate(1, 7, 1), candidate(2, 7, 1), candidate(3, 6, 1)],
        {"fantasy_average_recency_weighted": 1},
    )
    assert result["items"][0]["score"] == pytest.approx(75)
    assert result["items"][1]["score"] == pytest.approx(75)


def test_missing_weighted_metric_excludes_candidate() -> None:
    result = calculate_ranking(
        [candidate(1, 7, 1), candidate(2, None, 1)],
        {"fantasy_average_recency_weighted": 1},
    )
    assert result["eligible_pool_size"] == 1
    assert result["excluded"][0]["player_id"] == 2
    assert result["items"][0]["score"] == 100


def test_positive_trend_receives_the_higher_percentile() -> None:
    rising = candidate(1, 7, 1)
    falling = candidate(2, 7, 1)
    rising.metrics["fantasy_average_trend_slope"] = 0.25
    falling.metrics["fantasy_average_trend_slope"] = -0.10

    result = calculate_ranking(
        [rising, falling], {"fantasy_average_trend_slope": 1}
    )

    assert result["items"][0]["player_id"] == 1
    assert result["items"][0]["score"] == 100
    assert result["items"][0]["fantasy_average_trend_slope"] == 0.25


@pytest.mark.parametrize(
    "weights, message",
    [
        ({}, "almeno un peso"),
        ({"continuity": -1}, "negativi"),
        ({"unknown": 1}, "non supportate"),
    ],
)
def test_invalid_weights_are_rejected(weights: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        calculate_ranking([], weights)
