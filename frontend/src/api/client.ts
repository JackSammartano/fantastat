import type {
  DataQualityIssue,
  CompareResponse,
  CurrentListPage,
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
import { staticApi } from "./staticData";
import { currentListStore, filterCurrentList } from "../currentList/currentListStore";

export const IS_STATIC = import.meta.env.VITE_STATIC_MODE === "true";

const API_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ??
  "";

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

export interface CurrentListFilters {
  search?: string;
  role?: Role | "";
  team?: string;
  mappingStatus?: "certain_external_id" | "new_player" | "";
  minQuotation?: number;
  maxQuotation?: number;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export function getCurrentList(filters: CurrentListFilters = {}) {
  const imported = currentListStore.get();
  if (imported) return Promise.resolve(filterCurrentList(imported.items, filters));
  if (IS_STATIC) return staticApi.currentList(filters);
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.role) params.set("role", filters.role);
  if (filters.team) params.set("team", filters.team);
  if (filters.mappingStatus) params.set("mapping_status", filters.mappingStatus);
  if (filters.minQuotation !== undefined) params.set("min_quotation", String(filters.minQuotation));
  if (filters.maxQuotation !== undefined) params.set("max_quotation", String(filters.maxQuotation));
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.pageSize ?? 25));
  params.set("sort_by", filters.sortBy ?? "quotation");
  params.set("sort_order", filters.sortOrder ?? "desc");
  return request<CurrentListPage>(`/api/v1/current-list?${params}`);
}

export function getPlayers(filters: PlayerFilters = {}): Promise<PlayerPage> {
  if (IS_STATIC) return staticApi.players(filters);
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
  seasons: () => IS_STATIC ? staticApi.seasons() : request<Season[]>("/api/v1/seasons"),
  players: getPlayers,
  currentList: getCurrentList,
  player: async (id: number) => {
    const detail = IS_STATIC ? await staticApi.player(id) as PlayerDetail : await request<PlayerDetail>(`/api/v1/players/${id}`);
    const imported = currentListStore.get()?.items.find((item) => item.player_id === id);
    if (!detail || !imported) return detail;
    return { ...detail, current_list: { role: imported.classic_role, mantra_roles: imported.mantra_roles, team: imported.team, quotation: imported.quotation, initial_quotation: imported.initial_quotation, mantra_quotation: imported.mantra_quotation, initial_mantra_quotation: imported.initial_mantra_quotation, fvm: imported.fvm, fvm_mantra: imported.fvm_mantra, mapping_status: imported.mapping_status } };
  },
  comparePlayers: (ids: number[]) => {
    if (IS_STATIC) return staticApi.comparePlayers(ids);
    const params = new URLSearchParams();
    ids.forEach((id) => params.append("ids", String(id)));
    return request<CompareResponse>(`/api/v1/players/compare?${params}`);
  },
  rankingMetadata: () => IS_STATIC ? staticApi.rankingMetadata() :
    request<RankingMetadata>("/api/v1/rankings"),
  calculateRanking: (payload: RankingRequest) =>
    IS_STATIC || currentListStore.get() ? staticApi.calculateRanking(payload) : request<RankingResponse>("/api/v1/rankings/calculate", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  rankingConfigs: () => IS_STATIC ? staticApi.rankingConfigs() :
    request<RankingConfig[]>("/api/v1/ranking-configs"),
  saveRankingConfig: (name: string, configuration: RankingRequest) =>
    IS_STATIC ? staticApi.saveRankingConfig(name, configuration) : request<RankingConfig>("/api/v1/ranking-configs", {
      method: "POST",
      body: JSON.stringify({ name, configuration })
    }),
  deleteRankingConfig: (id: number) =>
    IS_STATIC ? staticApi.deleteRankingConfig(id) : request<void>(`/api/v1/ranking-configs/${id}`, { method: "DELETE" }),
  issues: () => IS_STATIC ? Promise.resolve([] as DataQualityIssue[]) : request<DataQualityIssue[]>("/api/v1/data-quality/issues"),
  pendingMappings: () =>
    IS_STATIC ? Promise.resolve([] as PendingMapping[]) : request<PendingMapping[]>("/api/v1/player-mappings/pending"),
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
