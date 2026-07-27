"""Importazione storica transazionale, idempotente e verificata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import create_database_engine
from backend.app.models import PlayerSeasonStats
from backend.pipeline.column_mapping import load_column_mapping
from backend.pipeline.importer import (
    PreparedRecord,
    persist_prepared_batch,
    summary_dict,
)
from backend.pipeline.matching import load_manual_mappings, match_records
from backend.pipeline.normalization import normalize_source_record
from backend.pipeline.validation import (
    RecordContext,
    load_validation_rules,
    validate_dataset,
)
from backend.scripts.inspect_excel import load_config, sha256_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa le stagioni in SQLite.")
    parser.add_argument(
        "--seasons-config",
        type=Path,
        default=Path("backend/config/seasons.yaml"),
    )
    parser.add_argument(
        "--column-mapping",
        type=Path,
        default=Path("backend/config/column_mapping.yaml"),
    )
    parser.add_argument(
        "--validation-rules",
        type=Path,
        default=Path("backend/config/validation_rules.yaml"),
    )
    parser.add_argument(
        "--manual-mappings",
        type=Path,
        default=Path("data/manual-mappings/player_mappings.json"),
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Override opzionale dell'URL SQLAlchemy.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("reports/import-summary"),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seasons = load_config(args.seasons_config.resolve())
    mapping = load_column_mapping(args.column_mapping.resolve())
    rules = load_validation_rules(args.validation_rules.resolve())
    manual = load_manual_mappings(args.manual_mappings.resolve())

    prepared: list[PreparedRecord] = []
    contexts: list[RecordContext] = []
    match_inputs = []
    excluded: list[dict[str, object]] = []

    for season in seasons.seasons:
        path = seasons.source_root / season["file"]
        file_hash = sha256_file(path)
        frame = pd.read_excel(
            path,
            sheet_name=seasons.canonical_sheet,
            header=seasons.header_row - 1,
        )
        start_year, end_year = map(int, season["code"].split("/"))
        for row_number, source_record in enumerate(
            frame.to_dict("records"),
            start=seasons.header_row + 1,
        ):
            try:
                normalized = normalize_source_record(source_record, mapping)
            except Exception as error:
                excluded.append(
                    {
                        "season": season["code"],
                        "source_file": path.name,
                        "source_row_number": row_number,
                        "reason": str(error),
                    }
                )
                continue
            context = RecordContext(
                season=season["code"],
                source_file=path.name,
                sheet_name=seasons.canonical_sheet,
                source_row_number=row_number,
                record=normalized.analytical,
            )
            contexts.append(context)
            prepared.append(
                PreparedRecord(
                    season_code=season["code"],
                    start_year=start_year,
                    end_year=end_year,
                    source_file=path.name,
                    source_sha256=file_hash,
                    sheet_name=seasons.canonical_sheet,
                    source_row_number=row_number,
                    raw=normalized.raw,
                    analytical=normalized.analytical,
                )
            )
            match_inputs.append((season["code"], normalized.analytical))

    validation = validate_dataset(contexts, rules, excluded_rows=len(excluded))
    if validation.errors or excluded:
        print(
            "Importazione annullata prima della transazione: "
            f"{len(validation.errors)} errori, {len(excluded)} righe escluse."
        )
        return 1

    warning_by_key = {
        (issue.season, issue.source_row_number): issue
        for issue in validation.warnings
    }
    prepared = [
        PreparedRecord(
            **{
                **record.__dict__,
                "quality_status": (
                    "warning"
                    if (record.season_code, record.source_row_number)
                    in warning_by_key
                    else "valid"
                ),
                "quality_notes": (
                    warning_by_key[
                        (record.season_code, record.source_row_number)
                    ].message
                    if (record.season_code, record.source_row_number)
                    in warning_by_key
                    else None
                ),
            }
        )
        for record in prepared
    ]
    matching = match_records(
        match_inputs,
        provider="fantacalcio",
        manual_mappings=manual,
    )

    engine = create_database_engine(args.database_url)
    with Session(engine) as session:
        with session.begin():
            summary = persist_prepared_batch(
                session,
                prepared,
                matching,
                provider="fantacalcio",
            )

    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        **summary_dict(summary),
        "validation_warning_count": len(validation.warnings),
        "matching_review_count": len(matching.reviews),
    }
    (report_dir / "import-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    processed_dir = args.processed_dir.resolve()
    processed_dir.mkdir(parents=True, exist_ok=True)
    with Session(engine) as session:
        rows = session.execute(
            select(
                PlayerSeasonStats.player_id,
                PlayerSeasonStats.season_id,
                PlayerSeasonStats.classic_role,
                PlayerSeasonStats.mantra_roles,
                PlayerSeasonStats.rated_appearances,
                PlayerSeasonStats.average_rating,
                PlayerSeasonStats.fantasy_average,
                PlayerSeasonStats.goals_scored,
                PlayerSeasonStats.goals_conceded,
                PlayerSeasonStats.penalties_saved,
                PlayerSeasonStats.penalties_taken,
                PlayerSeasonStats.penalties_scored,
                PlayerSeasonStats.penalties_missed,
                PlayerSeasonStats.assists,
                PlayerSeasonStats.yellow_cards,
                PlayerSeasonStats.red_cards,
                PlayerSeasonStats.own_goals,
                PlayerSeasonStats.quality_status,
            ).order_by(
                PlayerSeasonStats.season_id,
                PlayerSeasonStats.player_id,
            )
        ).mappings()
        pd.DataFrame(rows).to_csv(
            processed_dir / "player-season-stats.csv",
            index=False,
            encoding="utf-8-sig",
        )
    engine.dispose()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

