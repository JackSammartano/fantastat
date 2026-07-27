"""Valida tutte le stagioni senza persistenza e produce report distinti."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from backend.pipeline.column_mapping import load_column_mapping
from backend.pipeline.normalization import normalize_source_record
from backend.pipeline.validation import (
    RecordContext,
    ValidationIssue,
    issue_counts,
    load_validation_rules,
    validate_dataset,
)
from backend.scripts.inspect_excel import load_config


REPORT_FIELDS = [
    "severity",
    "code",
    "message",
    "season",
    "source_file",
    "sheet_name",
    "source_row_number",
    "external_player_id",
    "player_name",
    "field",
    "actual_value",
]


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _write_issues(path: Path, issues: Iterable[ValidationIssue]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for issue in issues:
            row = asdict(issue)
            row["actual_value"] = json.dumps(
                _json_safe(row["actual_value"]),
                ensure_ascii=False,
                sort_keys=True,
            )
            writer.writerow(row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida le stagioni storiche.")
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
        "--output-dir",
        type=Path,
        default=Path("reports/data-quality/validation"),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seasons = load_config(args.seasons_config.resolve())
    mapping = load_column_mapping(args.column_mapping.resolve())
    rules = load_validation_rules(args.validation_rules.resolve())
    contexts: list[RecordContext] = []
    excluded: list[dict[str, Any]] = []
    source_rows = 0

    for season in seasons.seasons:
        path = seasons.source_root / season["file"]
        frame = pd.read_excel(
            path,
            sheet_name=seasons.canonical_sheet,
            header=seasons.header_row - 1,
        )
        rows = frame.to_dict("records")
        source_rows += len(rows)
        for row_number, source_record in enumerate(rows, start=seasons.header_row + 1):
            try:
                normalized = normalize_source_record(source_record, mapping)
            except Exception as error:
                excluded.append(
                    {
                        "season": season["code"],
                        "source_file": path.name,
                        "sheet_name": seasons.canonical_sheet,
                        "source_row_number": row_number,
                        "reason": str(error),
                    }
                )
                continue
            contexts.append(
                RecordContext(
                    season=season["code"],
                    source_file=path.name,
                    sheet_name=seasons.canonical_sheet,
                    source_row_number=row_number,
                    record=normalized.analytical,
                )
            )

    result = validate_dataset(contexts, rules, excluded_rows=len(excluded))
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_issues(output_dir / "blocking-errors.csv", result.errors)
    _write_issues(output_dir / "warnings.csv", result.warnings)

    excluded_path = output_dir / "excluded-rows.csv"
    with excluded_path.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = [
            "season",
            "source_file",
            "sheet_name",
            "source_row_number",
            "reason",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(excluded)

    summary = {
        "validation_schema_version": rules.schema_version,
        "source_rows": source_rows,
        "normalized_rows": len(contexts),
        "excluded_rows": result.excluded_rows,
        "blocking_error_count": len(result.errors),
        "warning_count": len(result.warnings),
        "blocking_error_counts_by_code": issue_counts(result.errors),
        "warning_counts_by_code": issue_counts(result.warnings),
        "row_reconciliation_ok": source_rows
        == len(contexts) + result.excluded_rows,
    }
    (output_dir / "validation-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 1 if result.errors or result.excluded_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())

