"""Schema relazionale normalizzato del progetto."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Player(TimestampMixin, Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint(
            "external_provider",
            "external_player_id",
            name="uq_players_provider_external_id",
        ),
        CheckConstraint(
            "matching_status IN "
            "('certain_external_id','manual_confirmed','new_player',"
            "'possible_match','conflict','homonym')",
            name="ck_players_matching_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_provider: Mapped[str | None] = mapped_column(String(50))
    external_player_id: Mapped[str | None] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    matching_status: Mapped[str] = mapped_column(
        String(30), default="new_player", nullable=False
    )
    manual_notes: Mapped[str | None] = mapped_column(Text)

    aliases: Mapped[list["PlayerAlias"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    season_stats: Mapped[list["PlayerSeasonStats"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("end_year = start_year + 1", name="ck_seasons_consecutive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(9), nullable=False, unique=True)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True
    )


class PlayerAlias(Base):
    __tablename__ = "player_aliases"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "source_provider",
            "source_name",
            name="uq_player_aliases_player_provider_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    source_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    first_seen_season_id: Mapped[int | None] = mapped_column(
        ForeignKey("seasons.id")
    )
    last_seen_season_id: Mapped[int | None] = mapped_column(
        ForeignKey("seasons.id")
    )

    player: Mapped[Player] = relationship(back_populates="aliases")


class SourceImport(Base):
    __tablename__ = "source_imports"
    __table_args__ = (
        UniqueConstraint(
            "import_type", "source_sha256", name="uq_source_imports_type_sha256"
        ),
        CheckConstraint(
            "status IN ('pending','running','completed','failed')",
            name="ck_source_imports_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int | None] = mapped_column(ForeignKey("seasons.id"))
    import_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    row_count: Mapped[int | None] = mapped_column(Integer)

    records: Mapped[list["SourceRecord"]] = relationship(
        back_populates="source_import", cascade="all, delete-orphan"
    )


class SourceRecord(Base):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint(
            "import_id",
            "sheet_name",
            "source_row_number",
            name="uq_source_records_import_sheet_row",
        ),
        UniqueConstraint(
            "import_id", "record_hash", name="uq_source_records_import_hash"
        ),
        CheckConstraint(
            "validation_status IN ('pending','valid','warning','error','excluded')",
            name="ck_source_records_validation_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("source_imports.id", ondelete="CASCADE"), nullable=False
    )
    sheet_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    external_player_id: Mapped[str | None] = mapped_column(String(100), index=True)
    raw_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )

    source_import: Mapped[SourceImport] = relationship(back_populates="records")


class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "season_id", name="uq_player_season_stats_player_season"
        ),
        CheckConstraint(
            "classic_role IN ('P','D','C','A')",
            name="ck_player_season_stats_classic_role",
        ),
        CheckConstraint("rated_appearances >= 0", name="ck_stats_rated_nonnegative"),
        CheckConstraint(
            "average_rating IS NULL OR average_rating >= 0",
            name="ck_stats_average_nonnegative",
        ),
        CheckConstraint(
            "fantasy_average IS NULL OR fantasy_average >= 0",
            name="ck_stats_fantasy_nonnegative",
        ),
        CheckConstraint(
            "goals_scored >= 0 AND goals_conceded >= 0 "
            "AND penalties_saved >= 0 AND penalties_taken >= 0 "
            "AND penalties_scored >= 0 AND penalties_missed >= 0 "
            "AND assists >= 0 AND yellow_cards >= 0 "
            "AND red_cards >= 0 AND own_goals >= 0",
            name="ck_stats_additive_nonnegative",
        ),
        CheckConstraint(
            "penalties_taken = penalties_scored + penalties_missed",
            name="ck_stats_penalty_identity",
        ),
        CheckConstraint(
            "(rated_appearances = 0 AND average_rating IS NULL "
            "AND fantasy_average IS NULL AND has_valid_rating = 0) "
            "OR (rated_appearances > 0 AND average_rating IS NOT NULL "
            "AND fantasy_average IS NOT NULL AND has_valid_rating = 1)",
            name="ck_stats_rating_presence",
        ),
        CheckConstraint(
            "source_record_count >= 1", name="ck_stats_source_record_count"
        ),
        CheckConstraint(
            "quality_status IN ('valid','warning','error')",
            name="ck_player_season_stats_quality_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )
    classic_role: Mapped[str] = mapped_column(String(1), nullable=False)
    mantra_roles: Mapped[str] = mapped_column(String(100), nullable=False)
    rated_appearances: Mapped[int] = mapped_column(Integer, nullable=False)
    average_rating: Mapped[float | None] = mapped_column(Float)
    fantasy_average: Mapped[float | None] = mapped_column(Float)
    goals_scored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    goals_conceded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalties_saved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalties_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalties_scored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalties_missed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    red_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    own_goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_valid_rating: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_record_count: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    quality_status: Mapped[str] = mapped_column(
        String(20), default="valid", nullable=False
    )
    quality_notes: Mapped[str | None] = mapped_column(Text)

    player: Mapped[Player] = relationship(back_populates="season_stats")
    team_associations: Mapped[list["PlayerTeamSeason"]] = relationship(
        back_populates="player_season_stats", cascade="all, delete-orphan"
    )


class PlayerTeamSeason(Base):
    __tablename__ = "player_team_seasons"
    __table_args__ = (
        UniqueConstraint(
            "player_season_stats_id",
            "team_id",
            "association_type",
            name="uq_player_team_season_association",
        ),
        CheckConstraint(
            "association_type IN ('observed','final','partial','unknown')",
            name="ck_player_team_seasons_association_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_season_stats_id: Mapped[int] = mapped_column(
        ForeignKey("player_season_stats.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    association_type: Mapped[str] = mapped_column(
        String(20), default="observed", nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_records.id")
    )

    player_season_stats: Mapped[PlayerSeasonStats] = relationship(
        back_populates="team_associations"
    )


class PlayerMappingReview(TimestampMixin, Base):
    __tablename__ = "player_mapping_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','resolved','excluded')",
            name="ck_player_mapping_reviews_status",
        ),
        CheckConstraint(
            "similarity_score IS NULL OR "
            "(similarity_score >= 0 AND similarity_score <= 100)",
            name="ck_player_mapping_reviews_similarity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_record_id: Mapped[int] = mapped_column(
        ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False
    )
    suggested_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"))
    candidate_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"))
    similarity_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"))
    resolution: Mapped[str | None] = mapped_column(String(50))
    resolved_by: Mapped[str | None] = mapped_column(String(100))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class PlayerMergeAudit(Base):
    __tablename__ = "player_merge_audits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('applied','reverted')",
            name="ck_player_merge_audits_status",
        ),
        UniqueConstraint("review_id", name="uq_player_merge_audits_review"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("player_mapping_reviews.id"), nullable=False
    )
    source_player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), nullable=False
    )
    target_player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), nullable=False
    )
    moved_stats_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    moved_alias_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    moved_current_list_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    previous_statuses: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    preview_token: Mapped[str] = mapped_column(String(64), nullable=False)
    backup_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CurrentSeasonList(Base):
    __tablename__ = "current_season_list"
    __table_args__ = (
        UniqueConstraint(
            "season_id", "source_record_id", name="uq_current_list_season_record"
        ),
        CheckConstraint(
            "mapping_status IN "
            "('pending','certain_external_id','manual_confirmed','new_player',"
            "'possible_match','conflict','homonym','excluded')",
            name="ck_current_list_mapping_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"))
    source_record_id: Mapped[int] = mapped_column(
        ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False
    )
    external_player_id: Mapped[str | None] = mapped_column(String(100))
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    official_classic_role: Mapped[str] = mapped_column(String(1), nullable=False)
    official_mantra_roles: Mapped[str | None] = mapped_column(String(100))
    official_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    quotation: Mapped[float | None] = mapped_column(Float)
    initial_quotation: Mapped[float | None] = mapped_column(Float)
    mantra_quotation: Mapped[float | None] = mapped_column(Float)
    initial_mantra_quotation: Mapped[float | None] = mapped_column(Float)
    fvm: Mapped[float | None] = mapped_column(Float)
    fvm_mantra: Mapped[float | None] = mapped_column(Float)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    mapping_status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )


class RankingConfig(TimestampMixin, Base):
    __tablename__ = "ranking_configs"
    __table_args__ = (
        CheckConstraint(
            "role IS NULL OR role IN ('P','D','C','A')",
            name="ck_ranking_configs_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    role: Mapped[str | None] = mapped_column(String(1))
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
