export type Role = "P" | "D" | "C" | "A";
export type ReliabilityBand = "low" | "medium" | "high";

export interface Season {
  id: number;
  code: string;
  start_year: number;
  end_year: number;
  is_current: boolean;
}

export interface PlayerListItem {
  id: number;
  display_name: string;
  external_player_id: string | null;
  latest_season: string | null;
  latest_role: Role | null;
  latest_team: string | null;
  latest_rated_appearances: number | null;
  available_seasons: number;
  reliability_score: number;
  reliability_band: ReliabilityBand;
}

export interface PlayerPage {
  items: PlayerListItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface CurrentListItem {
  id: number;
  player_id: number;
  external_player_id: string | null;
  name: string;
  classic_role: Role;
  mantra_roles: string[];
  team: string;
  quotation: number | null;
  initial_quotation: number | null;
  quotation_change: number | null;
  mantra_quotation: number | null;
  initial_mantra_quotation: number | null;
  mantra_quotation_change: number | null;
  fvm: number | null;
  fvm_mantra: number | null;
  mapping_status: string;
  historical_seasons: number;
}

export interface CurrentListPage {
  items: CurrentListItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface PlayerHistory {
  season_id: number;
  season: string;
  role: Role;
  mantra_roles: string[];
  teams: string[];
  rated_appearances: number;
  average_rating: number | null;
  fantasy_average: number | null;
  goals_scored: number;
  goals_conceded: number;
  penalties_saved: number;
  penalties_taken: number;
  penalties_scored: number;
  penalties_missed: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  own_goals: number;
  quality_status: string;
  quality_notes: string | null;
}

export interface PlayerMetrics {
  total_pv: number;
  available_seasons: number;
  selected_seasons: number;
  seasons_with_pv: number;
  latest_calendar_season: string;
  latest_calendar_season_present: boolean;
  latest_calendar_season_pv: number;
  latest_available_season: string | null;
  latest_role: Role | null;
  average_rating_simple: number | null;
  average_rating_weighted: number | null;
  fantasy_average_simple: number | null;
  fantasy_average_weighted: number | null;
  latest_average_rating: number | null;
  latest_fantasy_average: number | null;
  fantasy_average_recency_weighted: number | null;
  fantasy_average_absolute_change: number | null;
  fantasy_average_percentage_change: number | null;
  average_rating_trend_slope: number | null;
  fantasy_average_trend_slope: number | null;
  goals_per_appearance: number | null;
  goals_conceded_per_appearance: number | null;
  penalties_saved_per_appearance: number | null;
  assists_per_appearance: number | null;
  continuity: number;
  fantasy_average_volatility: number | null;
  reliability_score: number;
  reliability_band: ReliabilityBand;
  shrinkage_weight: number;
  fantasy_average_shrunk: number | null;
  [key: string]: string | number | boolean | null;
}

export interface PlayerDetail {
  id: number;
  display_name: string;
  normalized_name: string;
  external_provider: string | null;
  external_player_id: string | null;
  matching_status: string;
  manual_notes: string | null;
  aliases: string[];
  history: PlayerHistory[];
  metrics: PlayerMetrics;
  current_list: {
    role: Role;
    mantra_roles: string[];
    team: string;
    quotation: number | null;
    initial_quotation: number | null;
    mantra_quotation: number | null;
    initial_mantra_quotation: number | null;
    fvm: number | null;
    fvm_mantra: number | null;
    mapping_status: string;
  } | null;
}

export interface CompareResponse {
  players: PlayerDetail[];
}

export interface RankingMetadata {
  normalization: "percentile";
  metrics: Array<{
    key: string;
    direction: "higher" | "lower";
    roles: Role[];
  }>;
}

export interface RankingRequest {
  role: Role;
  selected_seasons: string[];
  minimum_appearances: number;
  recency_decay: number;
  continuity_threshold: number;
  metric_weights: Record<string, number>;
}

export interface RankingMetricComponent {
  value: number;
  percentile: number;
  weight: number;
  contribution: number;
  direction: "higher" | "lower";
}

export interface RankingResponse {
  configuration: RankingRequest;
  initial_pool_size: number;
  eligible_pool_size: number;
  excluded: Array<{
    player_id: number;
    display_name: string;
    missing_metrics: string[];
  }>;
  items: Array<{
    position: number;
    player_id: number;
    display_name: string;
    score: number;
    reliability_score: number | null;
    total_pv: number | null;
    seasons_with_pv: number | null;
    fantasy_average_trend_slope: number | null;
    fantasy_average_absolute_change: number | null;
    metrics: Record<string, RankingMetricComponent>;
  }>;
}

export interface RankingConfig {
  id: number;
  name: string;
  role: Role;
  configuration: RankingRequest;
}

export interface DataQualityIssue {
  category: "data_quality" | "player_mapping";
  issue_id: number;
  status: string;
  player_name: string | null;
  season: string | null;
  message: string;
  source_row_number: number | null;
}

export interface PendingMapping {
  id: number;
  source_record_id: number;
  source_external_player_id: string | null;
  source_name: string | null;
  season: string | null;
  reason: string;
  notes: string | null;
  source_player_id: number | null;
  source_role: Role | null;
  source_team: string | null;
  source_rated_appearances: number | null;
  candidate: {
    player_id: number | null;
    display_name: string | null;
    similarity_score: number | null;
    roles: Role[];
    teams: string[];
    seasons: string[];
  };
}

export interface MappingResolution {
  resolution: "confirm_candidate" | "new_player" | "exclude";
  resolved_player_id?: number;
  notes?: string;
}

export interface MergePreview {
  review_id: number;
  source_player_id: number;
  target_player_id: number;
  source_name: string;
  target_name: string;
  preview_token: string;
  seasons_to_move: string[];
  alias_names_to_move: string[];
  overlapping_seasons: string[];
  alias_conflicts: string[];
  blocked: boolean;
  blockers: string[];
}

export interface MergeAudit {
  id: number;
  review_id: number;
  source_player_id: number;
  target_player_id: number;
  status: string;
  backup_path: string | null;
}
