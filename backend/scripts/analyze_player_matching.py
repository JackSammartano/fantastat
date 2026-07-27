"""Analisi read-only del matching storico e generazione report locali."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import pandas as pd

from backend.pipeline.column_mapping import load_column_mapping
from backend.pipeline.matching import (
    MATCH_STATUSES,
    REVIEW_STATUSES,
    load_manual_mappings,
    match_records,
)
from backend.pipeline.normalization import normalize_source_record
from backend.scripts.inspect_excel import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analizza il matching dei giocatori.")
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
        "--manual-mappings",
        type=Path,
        default=Path("data/manual-mappings/player_mappings.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/unmatched-players"),
    )
    parser.add_argument("--fuzzy-threshold", type=float, default=92.0)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seasons_config = load_config(args.seasons_config.resolve())
    column_mapping = load_column_mapping(args.column_mapping.resolve())
    manual_mappings = load_manual_mappings(args.manual_mappings.resolve())

    records = []
    for season in seasons_config.seasons:
        path = seasons_config.source_root / season["file"]
        frame = pd.read_excel(
            path,
            sheet_name=seasons_config.canonical_sheet,
            header=seasons_config.header_row - 1,
        )
        for source_record in frame.to_dict("records"):
            normalized = normalize_source_record(source_record, column_mapping)
            records.append((season["code"], normalized.analytical))

    result = match_records(
        records,
        provider="fantacalcio",
        manual_mappings=manual_mappings,
        fuzzy_threshold=args.fuzzy_threshold,
    )
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "matching_schema_version": 1,
        "provider": "fantacalcio",
        "fuzzy_threshold": args.fuzzy_threshold,
        "record_count": len(result.decisions),
        "identity_count": len(result.identities),
        "decision_counts": {
            status: sum(decision.status == status for decision in result.decisions)
            for status in sorted(MATCH_STATUSES)
        },
        "review_counts": {
            status: sum(review.review_type == status for review in result.reviews)
            for status in sorted(REVIEW_STATUSES)
        },
        "alias_variant_count": sum(
            len(identity.aliases) > 1 for identity in result.identities
        ),
        "identities": [
            {
                **asdict(identity),
                "aliases": sorted(identity.aliases),
                "external_keys": sorted(
                    [list(key) for key in identity.external_keys]
                ),
                "roles": sorted(identity.roles),
                "teams": sorted(identity.teams),
                "seasons": sorted(identity.seasons),
            }
            for identity in result.identities
        ],
        "reviews": [asdict(review) for review in result.reviews],
    }
    json_path = output_dir / "matching-analysis.json"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    csv_path = output_dir / "pending-reviews.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "review_type",
                "source_provider",
                "source_external_id",
                "source_name",
                "source_season",
                "reason",
                "candidates_json",
            ],
        )
        writer.writeheader()
        for review in result.reviews:
            row = asdict(review)
            row["candidates_json"] = json.dumps(
                row.pop("candidates"), ensure_ascii=False, sort_keys=True
            )
            writer.writerow(row)

    print(f"Record analizzati: {len(result.decisions)}")
    print(f"Identità distinte: {len(result.identities)}")
    print(f"Revisioni pendenti: {len(result.reviews)}")
    print(f"Report JSON: {json_path}")
    print(f"Report CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
