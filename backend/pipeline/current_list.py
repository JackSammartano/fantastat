"""Normalizzazione, validazione e persistenza del listone ufficiale corrente."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models import (
    CurrentSeasonList,
    Player,
    PlayerAlias,
    Season,
    SourceImport,
    SourceRecord,
    Team,
)
from backend.pipeline.importer import _get_or_create_team, record_hash
from backend.pipeline.normalization import (
    normalize_classic_role,
    normalize_mantra_roles,
    normalize_name,
    normalize_team,
    parse_decimal,
    parse_integer,
)


@dataclass(frozen=True)
class CurrentListConfig:
    season_code: str
    source_file: Path
    source_provider: str
    canonical_sheet: str
    ceded_sheet: str
    header_row: int
    role_sheets: Mapping[str, str]
    expected_columns: tuple[str, ...]


@dataclass(frozen=True)
class PreparedCurrentPlayer:
    source_row_number: int
    raw: Mapping[str, Any]
    external_player_id: str
    source_name: str
    normalized_name: str
    team_name: str
    normalized_team_name: str
    classic_role: str
    mantra_roles: tuple[str, ...]
    quotation: Decimal
    initial_quotation: Decimal
    mantra_quotation: Decimal
    initial_mantra_quotation: Decimal
    fvm: Decimal
    fvm_mantra: Decimal


@dataclass(frozen=True)
class CurrentListSummary:
    status: str
    source_rows: int
    imported_rows: int
    linked_existing_players: int
    new_players_created: int
    teams_created: int
    ceded_rows: int


def load_current_list_config(path: Path) -> CurrentListConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    source = Path(payload["source_file"])
    if not source.is_absolute():
        source = path.resolve().parents[2] / source
    return CurrentListConfig(
        season_code=payload["season_code"],
        source_file=source.resolve(),
        source_provider=payload["source_provider"],
        canonical_sheet=payload["canonical_sheet"],
        ceded_sheet=payload["ceded_sheet"],
        header_row=int(payload["header_row"]),
        role_sheets=dict(payload["role_sheets"]),
        expected_columns=tuple(payload["expected_columns"]),
    )


def _required_decimal(value: Any, field: str) -> Decimal:
    parsed = parse_decimal(value)
    if parsed is None or parsed < 0:
        raise ValueError(f"{field}: è richiesto un valore non negativo")
    return parsed


def normalize_current_player(raw: Mapping[str, Any], row_number: int) -> PreparedCurrentPlayer:
    external_id = parse_integer(raw.get("Id"))
    if external_id is None or external_id < 0:
        raise ValueError("Id: è richiesto un intero non negativo")
    name = normalize_name(raw.get("Nome"))
    team, normalized_team = normalize_team(raw.get("Squadra"))
    quotation = _required_decimal(raw.get("Qt.A"), "Qt.A")
    initial_quotation = _required_decimal(raw.get("Qt.I"), "Qt.I")
    mantra_quotation = _required_decimal(raw.get("Qt.A M"), "Qt.A M")
    initial_mantra = _required_decimal(raw.get("Qt.I M"), "Qt.I M")
    classic_diff = _required_decimal(raw.get("Diff."), "Diff.")
    mantra_diff = _required_decimal(raw.get("Diff.M"), "Diff.M")
    if quotation - initial_quotation != classic_diff:
        raise ValueError(f"riga {row_number}: Diff. non coincide con Qt.A - Qt.I")
    if mantra_quotation - initial_mantra != mantra_diff:
        raise ValueError(f"riga {row_number}: Diff.M non coincide con Qt.A M - Qt.I M")
    return PreparedCurrentPlayer(
        source_row_number=row_number,
        raw=dict(raw),
        external_player_id=str(external_id),
        source_name=name.display,
        normalized_name=name.normalized,
        team_name=team,
        normalized_team_name=normalized_team,
        classic_role=normalize_classic_role(raw.get("R")),
        mantra_roles=normalize_mantra_roles(raw.get("RM")),
        quotation=quotation,
        initial_quotation=initial_quotation,
        mantra_quotation=mantra_quotation,
        initial_mantra_quotation=initial_mantra,
        fvm=_required_decimal(raw.get("FVM"), "FVM"),
        fvm_mantra=_required_decimal(raw.get("FVM M"), "FVM M"),
    )


def inspect_and_prepare_current_list(
    config: CurrentListConfig,
) -> tuple[list[PreparedCurrentPlayer], int]:
    workbook = pd.ExcelFile(config.source_file, engine="openpyxl")
    required_sheets = {
        config.canonical_sheet,
        config.ceded_sheet,
        *config.role_sheets,
    }
    missing_sheets = required_sheets - set(workbook.sheet_names)
    if missing_sheets:
        raise ValueError(f"Fogli mancanti: {sorted(missing_sheets)}")
    frame = pd.read_excel(
        workbook,
        sheet_name=config.canonical_sheet,
        header=config.header_row - 1,
    )
    if tuple(frame.columns) != config.expected_columns:
        raise ValueError(
            f"Colonne inattese: {list(frame.columns)}; attese: {list(config.expected_columns)}"
        )
    prepared = [
        normalize_current_player(raw, row_number)
        for row_number, raw in enumerate(
            frame.to_dict("records"), start=config.header_row + 1
        )
    ]
    ids = [row.external_player_id for row in prepared]
    if len(ids) != len(set(ids)):
        raise ValueError("Il foglio Tutti contiene ID duplicati")

    canonical_by_role = {
        role: {row.external_player_id for row in prepared if row.classic_role == role}
        for role in ("P", "D", "C", "A")
    }
    for sheet, role in config.role_sheets.items():
        role_frame = pd.read_excel(workbook, sheet_name=sheet, header=config.header_row - 1)
        role_ids = {str(int(value)) for value in role_frame["Id"].tolist()}
        if role_ids != canonical_by_role[role]:
            raise ValueError(f"Il foglio {sheet} non coincide con Tutti per il ruolo {role}")
    ceded = pd.read_excel(
        workbook, sheet_name=config.ceded_sheet, header=config.header_row - 1
    )
    workbook.close()
    return prepared, len(ceded)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def persist_current_list(
    session: Session,
    rows: Sequence[PreparedCurrentPlayer],
    config: CurrentListConfig,
    *,
    source_sha256: str,
    ceded_rows: int,
) -> CurrentListSummary:
    existing = session.scalar(
        select(SourceImport).where(
            SourceImport.import_type == "current_list",
            SourceImport.source_sha256 == source_sha256,
        )
    )
    if existing is not None:
        return CurrentListSummary(
            "already_imported", len(rows), 0, 0, 0, 0, ceded_rows
        )

    start_year, end_year = map(int, config.season_code.split("/"))
    season = session.scalar(select(Season).where(Season.code == config.season_code))
    if season is None:
        season = Season(
            code=config.season_code,
            start_year=start_year,
            end_year=end_year,
            is_current=True,
        )
        session.add(season)
        session.flush()
    else:
        season.is_current = True
    session.execute(
        Season.__table__.update()
        .where(Season.id != season.id)
        .values(is_current=False)
    )

    source_import = SourceImport(
        season_id=season.id,
        import_type="current_list",
        source_filename=config.source_file.name,
        source_sha256=source_sha256,
        source_provider=config.source_provider,
        status="running",
        row_count=0,
    )
    session.add(source_import)
    session.flush()
    session.execute(delete(CurrentSeasonList).where(CurrentSeasonList.season_id == season.id))

    players = {
        player.external_player_id: player
        for player in session.scalars(
            select(Player).where(Player.external_provider == config.source_provider)
        )
        if player.external_player_id is not None
    }
    team_cache: dict[str, Team] = {}
    linked = created = teams_created = 0
    for row in rows:
        player = players.get(row.external_player_id)
        if player is None:
            player = Player(
                external_provider=config.source_provider,
                external_player_id=row.external_player_id,
                display_name=row.source_name,
                normalized_name=row.normalized_name,
                matching_status="new_player",
            )
            session.add(player)
            session.flush()
            players[row.external_player_id] = player
            created += 1
            mapping_status = "new_player"
        else:
            linked += 1
            mapping_status = "certain_external_id"

        source_record = SourceRecord(
            import_id=source_import.id,
            sheet_name=config.canonical_sheet,
            source_row_number=row.source_row_number,
            external_player_id=row.external_player_id,
            raw_payload_json={key: str(value) if isinstance(value, Decimal) else value for key, value in row.raw.items()},
            record_hash=record_hash(row.raw),
            validation_status="valid",
        )
        session.add(source_record)
        session.flush()
        team = team_cache.get(row.normalized_team_name)
        if team is None:
            team, was_created = _get_or_create_team(
                session, row.team_name, row.normalized_team_name
            )
            team_cache[row.normalized_team_name] = team
            teams_created += int(was_created)

        session.add(
            CurrentSeasonList(
                season_id=season.id,
                player_id=player.id,
                source_record_id=source_record.id,
                external_player_id=row.external_player_id,
                source_name=row.source_name,
                official_classic_role=row.classic_role,
                official_mantra_roles=";".join(row.mantra_roles),
                official_team_id=team.id,
                quotation=float(row.quotation),
                initial_quotation=float(row.initial_quotation),
                mantra_quotation=float(row.mantra_quotation),
                initial_mantra_quotation=float(row.initial_mantra_quotation),
                fvm=float(row.fvm),
                fvm_mantra=float(row.fvm_mantra),
                mapping_status=mapping_status,
            )
        )
        alias = session.scalar(
            select(PlayerAlias).where(
                PlayerAlias.player_id == player.id,
                PlayerAlias.source_provider == config.source_provider,
                PlayerAlias.source_name == row.source_name,
            )
        )
        if alias is None:
            session.add(
                PlayerAlias(
                    player_id=player.id,
                    source_name=row.source_name,
                    normalized_name=row.normalized_name,
                    source_provider=config.source_provider,
                    first_seen_season_id=season.id,
                    last_seen_season_id=season.id,
                )
            )
        elif alias.last_seen_season_id is None or session.get(
            Season, alias.last_seen_season_id
        ).start_year < season.start_year:
            alias.last_seen_season_id = season.id
        source_import.row_count += 1

    source_import.status = "completed"
    source_import.completed_at = datetime.now(timezone.utc)
    session.flush()
    return CurrentListSummary(
        "completed", len(rows), len(rows), linked, created, teams_created, ceded_rows
    )


def summary_dict(summary: CurrentListSummary) -> dict[str, Any]:
    return asdict(summary)
