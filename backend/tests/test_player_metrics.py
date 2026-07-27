from __future__ import annotations

import math

import pytest

from backend.analytics.player_metrics import (
    SeasonPerformance,
    calculate_player_metrics,
)


SEASONS = ("2022/2023", "2023/2024", "2024/2025", "2025/2026")


def _season(
    season: str,
    *,
    pv: int,
    mv: float | None,
    fm: float | None,
    goals: int = 0,
    assists: int = 0,
    goals_conceded: int = 0,
    penalties_saved: int = 0,
    role: str = "C",
) -> SeasonPerformance:
    return SeasonPerformance(
        season=season,
        role=role,
        rated_appearances=pv,
        average_rating=mv,
        fantasy_average=fm,
        goals_scored=goals,
        goals_conceded=goals_conceded,
        penalties_saved=penalties_saved,
        penalties_missed=0,
        assists=assists,
        yellow_cards=0,
        red_cards=0,
        own_goals=0,
    )


def test_simple_weighted_recent_and_change_metrics() -> None:
    records = [
        _season("2022/2023", pv=10, mv=5, fm=6, goals=1),
        _season("2023/2024", pv=30, mv=7, fm=8, goals=9, assists=4),
    ]

    metrics = calculate_player_metrics(
        records,
        SEASONS,
        role_mean_fantasy_average=7,
    )

    assert metrics.fantasy_average_simple == 7
    assert metrics.fantasy_average_weighted == 7.5
    assert metrics.average_rating_weighted == 6.5
    assert metrics.fantasy_average_recency_weighted == pytest.approx(7.6)
    assert metrics.average_rating_trend_slope == pytest.approx(2)
    assert metrics.fantasy_average_trend_slope == pytest.approx(2)
    assert metrics.fantasy_average_absolute_change == 2
    assert metrics.fantasy_average_percentage_change == pytest.approx(100 / 3)
    assert metrics.goals_per_appearance == 0.25
    assert metrics.assists_per_appearance == 0.1
    assert metrics.fm_mv_delta == 1


def test_goalkeeper_rates_are_per_rated_appearance() -> None:
    records = [
        _season(
            "2024/2025",
            pv=20,
            mv=6,
            fm=5.5,
            goals_conceded=24,
            penalties_saved=2,
            role="P",
        ),
        _season(
            "2025/2026",
            pv=10,
            mv=6.2,
            fm=6,
            goals_conceded=6,
            penalties_saved=1,
            role="P",
        ),
    ]

    metrics = calculate_player_metrics(records, SEASONS)

    assert metrics.goals_conceded_per_appearance == 1
    assert metrics.penalties_saved_per_appearance == 0.1


def test_missing_seasons_do_not_enter_averages_but_affect_coverage() -> None:
    records = [
        _season("2022/2023", pv=10, mv=6, fm=6),
        _season("2023/2024", pv=30, mv=7, fm=8),
    ]

    metrics = calculate_player_metrics(records, SEASONS)

    assert metrics.available_seasons == 2
    assert metrics.selected_seasons == 4
    assert metrics.coverage_component == 0.5
    assert metrics.latest_calendar_season_present is False
    assert metrics.latest_calendar_season_pv == 0
    assert metrics.latest_available_season == "2023/2024"
    assert metrics.fantasy_average_simple == 7


def test_continuity_volatility_and_reliability_formula() -> None:
    records = [
        _season("2022/2023", pv=10, mv=5, fm=6),
        _season("2023/2024", pv=30, mv=7, fm=8),
    ]

    metrics = calculate_player_metrics(records, SEASONS)

    assert metrics.continuity == 0.25
    assert metrics.fantasy_average_volatility == pytest.approx(math.sqrt(0.75))
    expected = 100 * (0.5 * (40 / 76) + 0.25 * 0.5 + 0.25 * 0)
    assert metrics.reliability_score == pytest.approx(expected)
    assert metrics.reliability_band == "low"


def test_latest_calendar_activity_drives_recent_component() -> None:
    record = _season("2025/2026", pv=19, mv=6, fm=7)

    metrics = calculate_player_metrics([record], SEASONS)

    assert metrics.recent_component == 1
    assert metrics.coverage_component == 0.25
    assert metrics.sample_component == 0.25
    assert metrics.reliability_score == 43.75
    assert metrics.reliability_band == "medium"


def test_zero_pv_does_not_create_zero_average_or_volatility() -> None:
    records = [
        _season("2024/2025", pv=0, mv=None, fm=None),
        _season("2025/2026", pv=10, mv=6, fm=7),
    ]

    metrics = calculate_player_metrics(records, SEASONS)

    assert metrics.fantasy_average_simple == 7
    assert metrics.fantasy_average_weighted == 7
    assert metrics.fantasy_average_volatility is None
    assert metrics.seasons_with_pv == 1


def test_shrinkage_is_optional_and_transparent() -> None:
    record = _season("2025/2026", pv=20, mv=6, fm=8)

    without_role_mean = calculate_player_metrics([record], SEASONS)
    with_role_mean = calculate_player_metrics(
        [record],
        SEASONS,
        role_mean_fantasy_average=6,
    )

    assert without_role_mean.fantasy_average_shrunk is None
    assert with_role_mean.shrinkage_weight == 0.5
    assert with_role_mean.fantasy_average_shrunk == 7
    assert with_role_mean.fantasy_average_weighted == 8


def test_invalid_parameters_and_duplicate_seasons_are_rejected() -> None:
    record = _season("2025/2026", pv=10, mv=6, fm=7)
    with pytest.raises(ValueError, match="decay"):
        calculate_player_metrics([record], SEASONS, decay=0)
    with pytest.raises(ValueError, match="Più record"):
        calculate_player_metrics([record, record], SEASONS)
