import type {
  DataQualityIssue,
  CompareResponse,
  MappingResolution,
  MergeAudit,
  MergePreview,
  PendingMapping,
  PlayerDetail,
  PlayerPage,
  RankingMetadata,
  RankingConfig,
  RankingRequest,
  RankingResponse,
  Role,
  Season
} from "../models/api";

const API_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new ApiError(body?.detail ?? "Errore API", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface PlayerFilters {
  search?: string;
  role?: Role | "";
  team?: string;
  minAppearances?: number;
  minSeasons?: number;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export function getPlayers(filters: PlayerFilters = {}): Promise<PlayerPage> {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.role) params.set("role", filters.role);
  if (filters.team) params.set("team", filters.team);
  if (filters.minAppearances !== undefined) {
    params.set("min_appearances", String(filters.minAppearances));
  }
  if (filters.minSeasons !== undefined) {
    params.set("min_seasons", String(filters.minSeasons));
  }
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.pageSize ?? 25));
  params.set("sort_by", filters.sortBy ?? "name");
  params.set("sort_order", filters.sortOrder ?? "asc");
  return request(`/api/v1/players?${params}`);
}

export const api = {
  seasons: () => request<Season[]>("/api/v1/seasons"),
  players: getPlayers,
  player: (id: number) => request<PlayerDetail>(`/api/v1/players/${id}`),
  comparePlayers: (ids: number[]) => {
    const params = new URLSearchParams();
    ids.forEach((id) => params.append("ids", String(id)));
    return request<CompareResponse>(`/api/v1/players/compare?${params}`);
  },
  rankingMetadata: () =>
    request<RankingMetadata>("/api/v1/rankings"),
  calculateRanking: (payload: RankingRequest) =>
    request<RankingResponse>("/api/v1/rankings/calculate", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  rankingConfigs: () =>
    request<RankingConfig[]>("/api/v1/ranking-configs"),
  saveRankingConfig: (name: string, configuration: RankingRequest) =>
    request<RankingConfig>("/api/v1/ranking-configs", {
      method: "POST",
      body: JSON.stringify({ name, configuration })
    }),
  deleteRankingConfig: (id: number) =>
    request<void>(`/api/v1/ranking-configs/${id}`, { method: "DELETE" }),
  issues: () => request<DataQualityIssue[]>("/api/v1/data-quality/issues"),
  pendingMappings: () =>
    request<PendingMapping[]>("/api/v1/player-mappings/pending"),
  resolveMapping: (id: number, payload: MappingResolution) =>
    request<{
      id: number;
      status: string;
      resolution: string;
      resolved_player_id: number | null;
    }>(`/api/v1/player-mappings/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  mergePreview: (id: number) =>
    request<MergePreview>(`/api/v1/player-mappings/${id}/merge-preview`),
  applyMerge: (id: number, previewToken: string, notes?: string) =>
    request<MergeAudit>(`/api/v1/player-mappings/${id}/merge`, {
      method: "POST",
      body: JSON.stringify({ preview_token: previewToken, notes })
    }),
  revertMerge: (auditId: number) =>
    request<MergeAudit>(`/api/v1/player-merges/${auditId}/revert`, {
      method: "POST"
    })
};
