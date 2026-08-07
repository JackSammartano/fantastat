"""Esporta uno snapshot pubblico read-only per GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.analytics.ranking import METRIC_DIRECTIONS, METRIC_ROLES
from backend.app.db.session import create_database_engine
from backend.app.models import Season
from backend.app.services.current_list_queries import list_current_players
from backend.app.services.player_queries import player_detail


def main() -> int:
    output = Path("frontend/public/data/snapshot.json").resolve()
    engine = create_database_engine()
    with Session(engine) as session:
        seasons = list(session.scalars(select(Season).order_by(Season.start_year)))
        current = list_current_players(session, page=1, page_size=1000)
        details = {
            str(item["player_id"]): player_detail(session, item["player_id"])
            for item in current["items"]
        }
        players = []
        for item in current["items"]:
            detail = details[str(item["player_id"])]
            metrics = detail["metrics"]
            history = detail["history"]
            players.append(
                {
                    "id": item["player_id"],
                    "display_name": item["name"],
                    "external_player_id": item["external_player_id"],
                    "latest_season": "2026/2027",
                    "latest_role": item["classic_role"],
                    "latest_team": item["team"],
                    "latest_rated_appearances": (
                        history[-1]["rated_appearances"] if history else None
                    ),
                    "available_seasons": len(history),
                    "reliability_score": metrics["reliability_score"],
                    "reliability_band": metrics["reliability_band"],
                }
            )
        snapshot = {
            "schema_version": 1,
            "season": "2026/2027",
            "seasons": [
                {
                    "id": season.id,
                    "code": season.code,
                    "start_year": season.start_year,
                    "end_year": season.end_year,
                    "is_current": season.is_current,
                }
                for season in seasons
            ],
            "current_list": current["items"],
            "players": players,
            "details": details,
            "ranking_metadata": {
                "normalization": "percentile",
                "metrics": [
                    {
                        "key": key,
                        "direction": direction,
                        "roles": list(METRIC_ROLES.get(key, ("P", "D", "C", "A"))),
                    }
                    for key, direction in METRIC_DIRECTIONS.items()
                ],
            },
        }
    engine.dispose()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Snapshot statico: {len(players)} giocatori, {output.stat().st_size} byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
