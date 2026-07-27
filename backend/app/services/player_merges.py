"""Anteprima, fusione reversibile e mapping manuale delle identità."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT
from backend.app.models import (
    CurrentSeasonList,
    Player,
    PlayerAlias,
    PlayerMappingReview,
    PlayerMergeAudit,
    PlayerSeasonStats,
    Season,
    SourceRecord,
)

DEFAULT_MAPPING_PATH = (
    PROJECT_ROOT / "data" / "manual-mappings" / "player_mappings.json"
)


def _source_player(session: Session, review: PlayerMappingReview) -> Player | None:
    source = session.get(SourceRecord, review.source_record_id)
    if source is None:
        return None
    return session.scalar(
        select(Player).where(
            Player.external_provider == "fantacalcio",
            Player.external_player_id == source.external_player_id,
        )
    )


def merge_preview(session: Session, review_id: int) -> dict[str, Any]:
    review = session.get(PlayerMappingReview, review_id)
    if review is None:
        raise ValueError("Revisione non trovata")
    if review.status != "pending":
        raise ValueError("La revisione non è più pendente")
    source = _source_player(session, review)
    target = (
        session.get(Player, review.candidate_player_id)
        if review.candidate_player_id
        else None
    )
    if source is None or target is None:
        raise ValueError("Identità sorgente o candidata non disponibile")
    if source.id == target.id:
        raise ValueError("Sorgente e candidato coincidono")

    source_stats = list(
        session.scalars(
            select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == source.id)
        )
    )
    target_stats = list(
        session.scalars(
            select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == target.id)
        )
    )
    target_seasons = {row.season_id for row in target_stats}
    overlapping_ids = sorted(
        row.season_id for row in source_stats if row.season_id in target_seasons
    )
    season_names = {
        season.id: season.code
        for season in session.scalars(select(Season))
    }
    source_aliases = list(
        session.scalars(select(PlayerAlias).where(PlayerAlias.player_id == source.id))
    )
    target_alias_keys = {
        (alias.source_provider, alias.source_name)
        for alias in session.scalars(
            select(PlayerAlias).where(PlayerAlias.player_id == target.id)
        )
    }
    alias_conflicts = sorted(
        alias.source_name
        for alias in source_aliases
        if (alias.source_provider, alias.source_name) in target_alias_keys
    )
    current_rows = list(
        session.scalars(
            select(CurrentSeasonList).where(CurrentSeasonList.player_id == source.id)
        )
    )
    blockers = []
    if overlapping_ids:
        blockers.append("Statistiche presenti per la stessa stagione")
    if alias_conflicts:
        blockers.append("Alias già presenti sul candidato")
    state = {
        "review_id": review.id,
        "source_player_id": source.id,
        "target_player_id": target.id,
        "stats_ids": sorted(row.id for row in source_stats),
        "alias_ids": sorted(row.id for row in source_aliases),
        "current_list_ids": sorted(row.id for row in current_rows),
        "overlapping_season_ids": overlapping_ids,
    }
    token = hashlib.sha256(
        json.dumps(state, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        **state,
        "preview_token": token,
        "source_name": source.display_name,
        "target_name": target.display_name,
        "seasons_to_move": [
            season_names[row.season_id] for row in source_stats
        ],
        "alias_names_to_move": [row.source_name for row in source_aliases],
        "overlapping_seasons": [season_names[item] for item in overlapping_ids],
        "alias_conflicts": alias_conflicts,
        "blocked": bool(blockers),
        "blockers": blockers,
    }


def _backup_database(session: Session) -> str | None:
    bind = session.get_bind()
    if bind.dialect.name != "sqlite" or not bind.url.database:
        return None
    source_path = Path(bind.url.database).resolve()
    if not source_path.exists():
        return None
    backup_dir = source_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_dir / f"{source_path.stem}-pre-merge-{timestamp}.db"
    with sqlite3.connect(source_path) as source_db, sqlite3.connect(
        backup_path
    ) as backup_db:
        source_db.backup(backup_db)
    return str(backup_path.relative_to(PROJECT_ROOT)) if source_path.is_relative_to(PROJECT_ROOT) else str(backup_path)


def _write_mapping(
    path: Path,
    source: Player,
    target: Player,
    *,
    remove: bool = False,
) -> bytes:
    original = path.read_bytes()
    document = json.loads(original.decode("utf-8"))
    key = (source.external_provider, source.external_player_id)
    mappings = document.setdefault("mappings", [])
    mappings = [
        item
        for item in mappings
        if (item.get("source_provider"), str(item.get("source_external_id"))) != key
    ]
    if not remove:
        mappings.append(
            {
                "source_provider": source.external_provider,
                "source_external_id": source.external_player_id,
                "target_provider": target.external_provider,
                "target_external_id": target.external_player_id,
                "note": "Confermato tramite revisione locale",
            }
        )
    document["mappings"] = sorted(
        mappings,
        key=lambda item: (
            item["source_provider"],
            str(item["source_external_id"]),
        ),
    )
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return original


def apply_merge(
    session: Session,
    review_id: int,
    preview_token: str,
    *,
    notes: str | None = None,
    mapping_path: Path = DEFAULT_MAPPING_PATH,
) -> PlayerMergeAudit:
    preview = merge_preview(session, review_id)
    if preview["preview_token"] != preview_token:
        raise ValueError("Anteprima scaduta: ricalcolare prima di applicare")
    if preview["blocked"]:
        raise ValueError("Fusione bloccata: " + "; ".join(preview["blockers"]))
    review = session.get(PlayerMappingReview, review_id)
    assert review is not None
    source = session.get(Player, preview["source_player_id"])
    target = session.get(Player, preview["target_player_id"])
    assert source is not None and target is not None

    backup_path = _backup_database(session)
    original_mapping = _write_mapping(mapping_path, source, target)
    try:
        for item_id in preview["stats_ids"]:
            session.get(PlayerSeasonStats, item_id).player_id = target.id
        for item_id in preview["alias_ids"]:
            session.get(PlayerAlias, item_id).player_id = target.id
        for item_id in preview["current_list_ids"]:
            session.get(CurrentSeasonList, item_id).player_id = target.id
        previous_statuses = {
            "source": source.matching_status,
            "target": target.matching_status,
        }
        source.matching_status = "manual_confirmed"
        target.matching_status = "manual_confirmed"
        review.status = "resolved"
        review.resolution = "confirm_candidate"
        review.resolved_player_id = target.id
        review.resolved_by = "local-user"
        review.resolved_at = datetime.now(timezone.utc)
        review.notes = notes or review.notes
        audit = PlayerMergeAudit(
            review_id=review.id,
            source_player_id=source.id,
            target_player_id=target.id,
            moved_stats_ids=preview["stats_ids"],
            moved_alias_ids=preview["alias_ids"],
            moved_current_list_ids=preview["current_list_ids"],
            previous_statuses=previous_statuses,
            preview_token=preview_token,
            backup_path=backup_path,
            status="applied",
        )
        session.add(audit)
        session.commit()
        session.refresh(audit)
        return audit
    except Exception:
        session.rollback()
        mapping_path.write_bytes(original_mapping)
        raise


def revert_merge(
    session: Session,
    audit_id: int,
    *,
    mapping_path: Path = DEFAULT_MAPPING_PATH,
) -> PlayerMergeAudit:
    audit = session.get(PlayerMergeAudit, audit_id)
    if audit is None:
        raise ValueError("Audit fusione non trovato")
    if audit.status != "applied":
        raise ValueError("La fusione è già stata annullata")
    source = session.get(Player, audit.source_player_id)
    target = session.get(Player, audit.target_player_id)
    review = session.get(PlayerMappingReview, audit.review_id)
    if source is None or target is None or review is None:
        raise ValueError("Dati della fusione non più disponibili")
    for item_id in audit.moved_stats_ids:
        item = session.get(PlayerSeasonStats, item_id)
        if item is None or item.player_id != target.id:
            raise ValueError("Lo stato delle statistiche è cambiato: rollback bloccato")
    for item_id in audit.moved_alias_ids:
        item = session.get(PlayerAlias, item_id)
        if item is None or item.player_id != target.id:
            raise ValueError("Lo stato degli alias è cambiato: rollback bloccato")

    _backup_database(session)
    original_mapping = _write_mapping(mapping_path, source, target, remove=True)
    try:
        for item_id in audit.moved_stats_ids:
            session.get(PlayerSeasonStats, item_id).player_id = source.id
        for item_id in audit.moved_alias_ids:
            session.get(PlayerAlias, item_id).player_id = source.id
        for item_id in audit.moved_current_list_ids:
            item = session.get(CurrentSeasonList, item_id)
            if item is not None:
                item.player_id = source.id
        source.matching_status = audit.previous_statuses["source"]
        target.matching_status = audit.previous_statuses["target"]
        review.status = "pending"
        review.resolution = None
        review.resolved_player_id = None
        review.resolved_by = None
        review.resolved_at = None
        audit.status = "reverted"
        audit.reverted_at = datetime.now(timezone.utc)
        session.commit()
        return audit
    except Exception:
        session.rollback()
        mapping_path.write_bytes(original_mapping)
        raise
