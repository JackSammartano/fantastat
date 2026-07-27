"""Persistenza transazionale e idempotente dei batch storici validati."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    Player,
    PlayerAlias,
    PlayerMappingReview,
    PlayerSeasonStats,
    PlayerTeamSeason,
    Season,
    SourceImport,
    SourceRecord,
    Team,
)
from backend.pipeline.matching import MatchResult


@dataclass(frozen=True)
class PreparedRecord:
    season_code: str
    start_year: int
    end_year: int
    source_file: str
    source_sha256: str
    sheet_name: str
    source_row_number: int
    raw: Mapping[str, Any]
    analytical: Mapping[str, Any]
    quality_status: str = "valid"
    quality_notes: str | None = None


@dataclass(frozen=True)
class ImportSummary:
    status: str
    source_files: int
    imported_files: int
    skipped_files: int
    source_rows: int
    imported_rows: int
    players_created: int
    aliases_created: int
    seasons_created: int
    teams_created: int
    stats_created: int
    mapping_reviews_created: int


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return str(value)


def record_hash(raw: Mapping[str, Any]) -> str:
    payload = json.dumps(
        _json_safe(raw),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _get_or_create_season(
    session: Session,
    prepared: PreparedRecord,
) -> tuple[Season, bool]:
    season = session.scalar(select(Season).where(Season.code == prepared.season_code))
    if season is not None:
        if (
            season.start_year != prepared.start_year
            or season.end_year != prepared.end_year
        ):
            raise ValueError(
                f"Stagione {prepared.season_code} già presente con anni differenti"
            )
        return season, False
    season = Season(
        code=prepared.season_code,
        start_year=prepared.start_year,
        end_year=prepared.end_year,
    )
    session.add(season)
    session.flush()
    return season, True


def _get_or_create_team(
    session: Session,
    display_name: str,
    normalized_name: str,
) -> tuple[Team, bool]:
    team = session.scalar(
        select(Team).where(Team.normalized_name == normalized_name)
    )
    if team is not None:
        return team, False
    team = Team(display_name=display_name, normalized_name=normalized_name)
    session.add(team)
    session.flush()
    return team, True


def _identity_maps(
    session: Session,
    match_result: MatchResult,
) -> tuple[dict[str, Player], int]:
    players: dict[str, Player] = {}
    created = 0
    for identity in match_result.identities:
        player = session.scalar(
            select(Player).where(
                Player.external_provider == identity.primary_provider,
                Player.external_player_id == identity.primary_external_id,
            )
        )
        if player is None:
            player = Player(
                external_provider=identity.primary_provider,
                external_player_id=identity.primary_external_id,
                display_name=identity.display_name,
                normalized_name=identity.normalized_name,
                matching_status="certain_external_id",
            )
            session.add(player)
            session.flush()
            created += 1
        players[identity.internal_key] = player
    return players, created


def persist_prepared_batch(
    session: Session,
    prepared_records: Sequence[PreparedRecord],
    match_result: MatchResult,
    *,
    provider: str,
) -> ImportSummary:
    """Persiste un batch già normalizzato e validato nella transazione chiamante."""

    if len(prepared_records) != len(match_result.decisions):
        raise ValueError("Record preparati e decisioni di matching non allineati")

    files = {
        (record.source_file, record.source_sha256) for record in prepared_records
    }
    existing_hashes = set(
        session.scalars(
            select(SourceImport.source_sha256).where(
                SourceImport.import_type == "season",
                SourceImport.source_sha256.in_([sha for _, sha in files]),
            )
        )
    )
    new_hashes = {sha for _, sha in files} - existing_hashes
    if not new_hashes:
        return ImportSummary(
            status="already_imported",
            source_files=len(files),
            imported_files=0,
            skipped_files=len(files),
            source_rows=len(prepared_records),
            imported_rows=0,
            players_created=0,
            aliases_created=0,
            seasons_created=0,
            teams_created=0,
            stats_created=0,
            mapping_reviews_created=0,
        )

    players_by_internal, players_created = _identity_maps(session, match_result)
    decisions_by_record = list(zip(prepared_records, match_result.decisions, strict=True))
    season_cache: dict[str, Season] = {}
    team_cache: dict[str, Team] = {}
    import_cache: dict[str, SourceImport] = {}
    source_record_lookup: dict[tuple[str, str], SourceRecord] = {}
    seasons_created = teams_created = aliases_created = stats_created = 0
    imported_rows = 0

    for prepared, decision in decisions_by_record:
        if prepared.source_sha256 not in new_hashes:
            continue
        season = season_cache.get(prepared.season_code)
        if season is None:
            season, was_created = _get_or_create_season(session, prepared)
            seasons_created += int(was_created)
            season_cache[prepared.season_code] = season

        source_import = import_cache.get(prepared.source_sha256)
        if source_import is None:
            source_import = SourceImport(
                season_id=season.id,
                import_type="season",
                source_filename=prepared.source_file,
                source_sha256=prepared.source_sha256,
                source_provider=provider,
                started_at=datetime.now(timezone.utc),
                status="running",
                row_count=0,
            )
            session.add(source_import)
            session.flush()
            import_cache[prepared.source_sha256] = source_import

        player = players_by_internal[decision.internal_key]
        raw_payload = _json_safe(prepared.raw)
        source_record = SourceRecord(
            import_id=source_import.id,
            sheet_name=prepared.sheet_name,
            source_row_number=prepared.source_row_number,
            external_player_id=str(prepared.analytical["external_player_id"]),
            raw_payload_json=raw_payload,
            record_hash=record_hash(prepared.raw),
            validation_status=(
                "warning" if prepared.quality_status == "warning" else "valid"
            ),
        )
        session.add(source_record)
        session.flush()
        source_record_lookup[
            (prepared.season_code, str(prepared.analytical["external_player_id"]))
        ] = source_record

        normalized_team = str(prepared.analytical["normalized_team_name"])
        team = team_cache.get(normalized_team)
        if team is None:
            team, was_created = _get_or_create_team(
                session,
                str(prepared.analytical["source_team_name"]),
                normalized_team,
            )
            teams_created += int(was_created)
            team_cache[normalized_team] = team

        stats = PlayerSeasonStats(
            player_id=player.id,
            season_id=season.id,
            classic_role=str(prepared.analytical["classic_role"]),
            mantra_roles=";".join(prepared.analytical["mantra_roles"]),
            rated_appearances=int(prepared.analytical["rated_appearances"]),
            average_rating=(
                float(prepared.analytical["average_rating"])
                if prepared.analytical["average_rating"] is not None
                else None
            ),
            fantasy_average=(
                float(prepared.analytical["fantasy_average"])
                if prepared.analytical["fantasy_average"] is not None
                else None
            ),
            goals_scored=int(prepared.analytical["goals_scored"]),
            goals_conceded=int(prepared.analytical["goals_conceded"]),
            penalties_saved=int(prepared.analytical["penalties_saved"]),
            penalties_taken=int(prepared.analytical["penalties_taken"]),
            penalties_scored=int(prepared.analytical["penalties_scored"]),
            penalties_missed=int(prepared.analytical["penalties_missed"]),
            assists=int(prepared.analytical["assists"]),
            yellow_cards=int(prepared.analytical["yellow_cards"]),
            red_cards=int(prepared.analytical["red_cards"]),
            own_goals=int(prepared.analytical["own_goals"]),
            has_valid_rating=bool(prepared.analytical["has_valid_rating"]),
            source_record_count=1,
            quality_status=prepared.quality_status,
            quality_notes=prepared.quality_notes,
        )
        session.add(stats)
        session.flush()
        session.add(
            PlayerTeamSeason(
                player_season_stats_id=stats.id,
                team_id=team.id,
                association_type="observed",
                is_primary=True,
                source_record_id=source_record.id,
            )
        )

        alias = session.scalar(
            select(PlayerAlias).where(
                PlayerAlias.player_id == player.id,
                PlayerAlias.source_provider == provider,
                PlayerAlias.source_name
                == str(prepared.analytical["source_player_name"]),
            )
        )
        if alias is None:
            alias = PlayerAlias(
                player_id=player.id,
                source_name=str(prepared.analytical["source_player_name"]),
                normalized_name=str(prepared.analytical["normalized_player_name"]),
                source_provider=provider,
                first_seen_season_id=season.id,
                last_seen_season_id=season.id,
            )
            session.add(alias)
            aliases_created += 1
        else:
            if alias.first_seen_season_id is None or season.start_year < session.get(
                Season, alias.first_seen_season_id
            ).start_year:
                alias.first_seen_season_id = season.id
            if alias.last_seen_season_id is None or season.start_year > session.get(
                Season, alias.last_seen_season_id
            ).start_year:
                alias.last_seen_season_id = season.id

        source_import.row_count = int(source_import.row_count or 0) + 1
        stats_created += 1
        imported_rows += 1

    for source_import in import_cache.values():
        source_import.status = "completed"
        source_import.completed_at = datetime.now(timezone.utc)

    mapping_reviews_created = 0
    for review in match_result.reviews:
        source_record = source_record_lookup.get(
            (review.source_season, review.source_external_id)
        )
        if source_record is None:
            continue
        candidate = review.candidates[0] if review.candidates else None
        session.add(
            PlayerMappingReview(
                source_record_id=source_record.id,
                suggested_player_id=(
                    players_by_internal[candidate.internal_key].id
                    if candidate is not None
                    else None
                ),
                candidate_player_id=(
                    players_by_internal[candidate.internal_key].id
                    if candidate is not None
                    else None
                ),
                similarity_score=candidate.score if candidate is not None else None,
                status="pending",
                reason=review.reason,
                notes=f"Tipo revisione: {review.review_type}",
            )
        )
        mapping_reviews_created += 1

    session.flush()
    return ImportSummary(
        status="completed",
        source_files=len(files),
        imported_files=len(new_hashes),
        skipped_files=len(existing_hashes),
        source_rows=len(prepared_records),
        imported_rows=imported_rows,
        players_created=players_created,
        aliases_created=aliases_created,
        seasons_created=seasons_created,
        teams_created=teams_created,
        stats_created=stats_created,
        mapping_reviews_created=mapping_reviews_created,
    )


def summary_dict(summary: ImportSummary) -> dict[str, Any]:
    return asdict(summary)

