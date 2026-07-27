"""Calcola metriche derivate dal database e le esporta senza persisterle."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import text

from backend.analytics.player_metrics import (
    SeasonPerformance,
    calculate_player_metrics,
    metrics_dict,
)
from backend.app.db.session import create_database_engine


QUERY = text(
    """
    SELECT
        p.id AS player_id,
        p.display_name,
        s.code AS season,
        s.start_year,
        ps.classic_role AS role,
        ps.rated_appearances,
        ps.average_rating,
        ps.fantasy_average,
        ps.goals_scored,
        ps.goals_conceded,
        ps.penalties_saved,
        ps.penalties_missed,
        ps.assists,
        ps.yellow_cards,
        ps.red_cards,
        ps.own_goals
    FROM player_season_stats ps
    JOIN players p ON p.id = ps.player_id
    JOIN seasons s ON s.id = ps.season_id
    ORDER BY p.id, s.start_year
    """
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calcola le metriche giocatore.")
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument("--decay", type=float, default=0.75)
    parser.add_argument("--continuity-threshold", type=int, default=19)
    parser.add_argument("--shrinkage-k", type=float, default=20)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = create_database_engine(args.database_url)
    with engine.connect() as connection:
        frame = pd.read_sql_query(QUERY, connection)
    engine.dispose()
    if frame.empty:
        print("Database privo di statistiche giocatore-stagione.")
        return 1

    seasons = (
        frame[["season", "start_year"]]
        .drop_duplicates()
        .sort_values("start_year")["season"]
        .tolist()
    )
    player_records: dict[int, list[SeasonPerformance]] = defaultdict(list)
    display_names: dict[int, str] = {}
    for row in frame.itertuples(index=False):
        display_names[row.player_id] = row.display_name
        player_records[row.player_id].append(
            SeasonPerformance(
                season=row.season,
                role=row.role,
                rated_appearances=int(row.rated_appearances),
                average_rating=(
                    float(row.average_rating)
                    if pd.notna(row.average_rating)
                    else None
                ),
                fantasy_average=(
                    float(row.fantasy_average)
                    if pd.notna(row.fantasy_average)
                    else None
                ),
                goals_scored=int(row.goals_scored),
                goals_conceded=int(row.goals_conceded),
                penalties_saved=int(row.penalties_saved),
                penalties_missed=int(row.penalties_missed),
                assists=int(row.assists),
                yellow_cards=int(row.yellow_cards),
                red_cards=int(row.red_cards),
                own_goals=int(row.own_goals),
            )
        )

    preliminary = {
        player_id: calculate_player_metrics(records, seasons)
        for player_id, records in player_records.items()
    }
    role_numerator: dict[str, float] = defaultdict(float)
    role_denominator: dict[str, int] = defaultdict(int)
    for metrics in preliminary.values():
        if (
            metrics.latest_role is not None
            and metrics.fantasy_average_weighted is not None
            and metrics.total_pv > 0
        ):
            role_numerator[metrics.latest_role] += (
                metrics.fantasy_average_weighted * metrics.total_pv
            )
            role_denominator[metrics.latest_role] += metrics.total_pv
    role_means = {
        role: role_numerator[role] / denominator
        for role, denominator in role_denominator.items()
        if denominator
    }

    rows = []
    for player_id, records in player_records.items():
        role = preliminary[player_id].latest_role
        metrics = calculate_player_metrics(
            records,
            seasons,
            decay=args.decay,
            continuity_threshold=args.continuity_threshold,
            shrinkage_k=args.shrinkage_k,
            role_mean_fantasy_average=role_means.get(role),
        )
        rows.append(
            {
                "player_id": player_id,
                "display_name": display_names[player_id],
                **metrics_dict(metrics),
            }
        )

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "player-metrics.csv"
    result_frame = pd.DataFrame(rows).sort_values("player_id")
    result_frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    summary = {
        "player_count": len(result_frame),
        "selected_seasons": seasons,
        "decay": args.decay,
        "continuity_threshold": args.continuity_threshold,
        "shrinkage_k": args.shrinkage_k,
        "role_mean_fantasy_average": role_means,
        "reliability_band_counts": result_frame[
            "reliability_band"
        ].value_counts().sort_index().to_dict(),
        "players_without_weighted_fantasy_average": int(
            result_frame["fantasy_average_weighted"].isna().sum()
        ),
        "output": str(output_path),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

