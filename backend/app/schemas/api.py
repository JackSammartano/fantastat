from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SeasonResponse(BaseModel):
    id: int
    code: str
    start_year: int
    end_year: int
    is_current: bool


class PlayerHistoryItem(BaseModel):
    season_id: int
    season: str
    role: str
    mantra_roles: list[str]
    teams: list[str]
    rated_appearances: int
    average_rating: float | None
    fantasy_average: float | None
    goals_scored: int
    goals_conceded: int
    penalties_saved: int
    penalties_taken: int
    penalties_scored: int
    penalties_missed: int
    assists: int
    yellow_cards: int
    red_cards: int
    own_goals: int
    quality_status: str
    quality_notes: str | None


class PlayerListItem(BaseModel):
    id: int
    display_name: str
    external_player_id: str | None
    latest_season: str | None
    latest_role: str | None
    latest_team: str | None
    latest_rated_appearances: int | None
    available_seasons: int
    reliability_score: float
    reliability_band: str


class PlayerPage(BaseModel):
    items: list[PlayerListItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class CurrentListItem(BaseModel):
    id: int
    player_id: int
    external_player_id: str | None
    name: str
    classic_role: Literal["P", "D", "C", "A"]
    mantra_roles: list[str]
    team: str
    quotation: float | None
    initial_quotation: float | None
    quotation_change: float | None
    mantra_quotation: float | None
    initial_mantra_quotation: float | None
    mantra_quotation_change: float | None
    fvm: float | None
    fvm_mantra: float | None
    mapping_status: str
    historical_seasons: int


class CurrentListPage(BaseModel):
    items: list[CurrentListItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PlayerDetailResponse(BaseModel):
    id: int
    display_name: str
    normalized_name: str
    external_provider: str | None
    external_player_id: str | None
    matching_status: str
    manual_notes: str | None
    aliases: list[str]
    history: list[PlayerHistoryItem]
    metrics: dict[str, Any]
    current_list: "PlayerCurrentListResponse | None"


class PlayerCurrentListResponse(BaseModel):
    role: Literal["P", "D", "C", "A"]
    mantra_roles: list[str]
    team: str
    quotation: float | None
    initial_quotation: float | None
    mantra_quotation: float | None
    initial_mantra_quotation: float | None
    fvm: float | None
    fvm_mantra: float | None
    mapping_status: str


class CompareResponse(BaseModel):
    players: list[PlayerDetailResponse]


class DataQualityIssueResponse(BaseModel):
    category: str
    issue_id: int
    status: str
    player_name: str | None
    season: str | None
    message: str
    source_row_number: int | None


class MappingCandidateResponse(BaseModel):
    player_id: int | None
    display_name: str | None
    similarity_score: float | None
    roles: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    seasons: list[str] = Field(default_factory=list)


class PendingMappingResponse(BaseModel):
    id: int
    source_record_id: int
    source_external_player_id: str | None
    source_name: str | None
    season: str | None
    reason: str
    notes: str | None
    source_player_id: int | None
    source_role: str | None
    source_team: str | None
    source_rated_appearances: int | None
    candidate: MappingCandidateResponse


class ResolveMappingRequest(BaseModel):
    resolution: Literal["confirm_candidate", "new_player", "exclude"]
    resolved_player_id: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=2000)


class ResolveMappingResponse(BaseModel):
    id: int
    status: str
    resolution: str
    resolved_player_id: int | None


class ApplyMergeRequest(BaseModel):
    preview_token: str = Field(min_length=64, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class MergeAuditResponse(BaseModel):
    id: int
    review_id: int
    source_player_id: int
    target_player_id: int
    status: str
    backup_path: str | None


class ErrorResponse(BaseModel):
    error: str
    detail: str


class RankingRequest(BaseModel):
    role: Literal["P", "D", "C", "A"]
    selected_seasons: list[str] = Field(min_length=1)
    minimum_appearances: int = Field(default=1, ge=0, le=152)
    recency_decay: float = Field(default=0.75, gt=0, le=1)
    continuity_threshold: int = Field(default=19, ge=0, le=38)
    metric_weights: dict[str, float]


class RankingMetricComponent(BaseModel):
    value: float
    percentile: float
    weight: float
    contribution: float
    direction: Literal["higher", "lower"]


class RankingItemResponse(BaseModel):
    position: int
    player_id: int
    display_name: str
    score: float
    reliability_score: float | None
    total_pv: int | None
    seasons_with_pv: int | None
    fantasy_average_trend_slope: float | None
    fantasy_average_absolute_change: float | None
    metrics: dict[str, RankingMetricComponent]


class RankingExcludedResponse(BaseModel):
    player_id: int
    display_name: str
    missing_metrics: list[str]


class RankingResponse(BaseModel):
    configuration: dict[str, Any]
    initial_pool_size: int
    eligible_pool_size: int
    excluded: list[RankingExcludedResponse]
    items: list[RankingItemResponse]


class RankingConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    configuration: RankingRequest


class RankingConfigResponse(BaseModel):
    id: int
    name: str
    role: str
    configuration: RankingRequest
