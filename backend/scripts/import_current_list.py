"""CLI per validare e importare il listone ufficiale 2026/2027."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.session import create_database_engine
from backend.pipeline.current_list import (
    inspect_and_prepare_current_list,
    load_current_list_config,
    persist_current_list,
    sha256_file,
    summary_dict,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa il listone ufficiale corrente.")
    parser.add_argument(
        "--config", type=Path, default=Path("backend/config/current_list.yaml")
    )
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument(
        "--report-dir", type=Path, default=Path("reports/current-list-import")
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_current_list_config(args.config.resolve())
    rows, ceded_rows = inspect_and_prepare_current_list(config)
    digest = sha256_file(config.source_file)
    engine = create_database_engine(args.database_url)
    with Session(engine) as session, session.begin():
        summary = persist_current_list(
            session,
            rows,
            config,
            source_sha256=digest,
            ceded_rows=ceded_rows,
        )
    engine.dispose()
    report = {**summary_dict(summary), "source_sha256": digest}
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "import-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
