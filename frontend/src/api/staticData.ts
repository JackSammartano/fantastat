import type {
  CompareResponse,
  CurrentListItem,
  CurrentListPage,
  PlayerDetail,
  PlayerHistory,
  PlayerPage,
  RankingConfig,
  RankingMetadata,
  RankingRequest,
  RankingResponse,
  Season
} from "../models/api";
import type { CurrentListFilters, PlayerFilters } from "./client";
import { currentListStore, filterCurrentList } from "../currentList/currentListStore";

interface StaticSnapshot {
  schema_version: number;
  season: string;
  seasons: Season[];
  current_list: CurrentListItem[];
  players: PlayerPage["items"];
  details: Record<string, PlayerDetail>;
  ranking_metadata: RankingMetadata;
}

let snapshotPromise: Promise<StaticSnapshot> | null = null;

function snapshot() {
  snapshotPromise ??= fetch(`${import.meta.env.BASE_URL}data/snapshot.json`).then(
    async (response) => {
      if (!response.ok) throw new Error("Snapshot pubblico non disponibile");
      return response.json() as Promise<StaticSnapshot>;
    }
  );
  return snapshotPromise;
}

function page<T>(items: T[], pageNumber = 1, pageSize = 25) {
  return {
    items: items.slice((pageNumber - 1) * pageSize, pageNumber * pageSize),
    page: pageNumber,
    page_size: pageSize,
    total_items: items.length,
    total_pages: items.length ? Math.ceil(items.length / pageSize) : 0
  };
}

export async function staticCurrentList(filters: CurrentListFilters = {}): Promise<CurrentListPage> {
  return filterCurrentList(currentListStore.get()?.items ?? (await snapshot()).current_list, filters);
}

export async function staticPlayers(filters: PlayerFilters = {}): Promise<PlayerPage> {
  let items = [...(await snapshot()).players];
  if (filters.search) items = items.filter((item) => item.display_name.toLocaleLowerCase("it").includes(filters.search!.toLocaleLowerCase("it")));
  if (filters.role) items = items.filter((item) => item.latest_role === filters.role);
  if (filters.team) items = items.filter((item) => item.latest_team?.toLocaleLowerCase("it") === filters.team!.toLocaleLowerCase("it"));
  if (filters.minAppearances !== undefined) items = items.filter((item) => (item.latest_rated_appearances ?? 0) >= filters.minAppearances!);
  if (filters.minSeasons !== undefined) items = items.filter((item) => item.available_seasons >= filters.minSeasons!);
  const sort = filters.sortBy ?? "name";
  items.sort((a, b) => sort === "name" ? a.display_name.localeCompare(b.display_name, "it") : (b.latest_rated_appearances ?? 0) - (a.latest_rated_appearances ?? 0));
  if (filters.sortOrder === "desc" && sort === "name") items.reverse();
  return page(items, filters.page, filters.pageSize);
}

export async function staticPlayer(id: number) {
  return (await snapshot()).details[String(id)] ?? null;
}

export async function staticCompare(ids: number[]): Promise<CompareResponse> {
  const data = await snapshot();
  return { players: ids.map((id) => data.details[String(id)]).filter(Boolean) };
}

const weighted = (rows: PlayerHistory[], field: "average_rating" | "fantasy_average", extra?: Map<string, number>) => {
  let numerator = 0;
  let denominator = 0;
  rows.forEach((row) => {
    const value = row[field];
    if (value === null || row.rated_appearances <= 0) return;
    const weight = row.rated_appearances * (extra?.get(row.season) ?? 1);
    numerator += value * weight;
    denominator += weight;
  });
  return denominator ? numerator / denominator : null;
};

function metrics(history: PlayerHistory[], request: RankingRequest) {
  const position = new Map(request.selected_seasons.map((season, index) => [season, index]));
  const rows = history.filter((row) => position.has(row.season)).sort((a, b) => position.get(a.season)! - position.get(b.season)!);
  const positive = rows.filter((row) => row.rated_appearances > 0);
  const total = rows.reduce((sum, row) => sum + row.rated_appearances, 0);
  const recency = new Map(request.selected_seasons.map((season, index) => [season, request.recency_decay ** (request.selected_seasons.length - 1 - index)]));
  const latest = positive.at(-1);
  const previous = positive.at(-2);
  const sum = (field: keyof PlayerHistory) => rows.reduce((value, row) => value + Number(row[field] ?? 0), 0);
  const fm = weighted(rows, "fantasy_average");
  const validFm = positive.filter((row) => row.fantasy_average !== null);
  let volatility: number | null = null;
  let slope: number | null = null;
  if (fm !== null && validFm.length >= 2) {
    volatility = Math.sqrt(validFm.reduce((value, row) => value + row.rated_appearances * (row.fantasy_average! - fm) ** 2, 0) / validFm.reduce((value, row) => value + row.rated_appearances, 0));
    const weightTotal = validFm.reduce((value, row) => value + row.rated_appearances, 0);
    const meanX = validFm.reduce((value, row) => value + position.get(row.season)! * row.rated_appearances, 0) / weightTotal;
    const meanY = validFm.reduce((value, row) => value + row.fantasy_average! * row.rated_appearances, 0) / weightTotal;
    const numerator = validFm.reduce((value, row) => value + row.rated_appearances * (position.get(row.season)! - meanX) * (row.fantasy_average! - meanY), 0);
    const denominator = validFm.reduce((value, row) => value + row.rated_appearances * (position.get(row.season)! - meanX) ** 2, 0);
    slope = denominator ? numerator / denominator : null;
  }
  const latestCalendar = rows.find((row) => row.season === request.selected_seasons.at(-1));
  const sample = Math.min(total / 76, 1);
  const coverage = rows.length / request.selected_seasons.length;
  const recent = Math.min((latestCalendar?.rated_appearances ?? 0) / 19, 1);
  return {
    total_pv: total,
    seasons_with_pv: positive.length,
    fantasy_average_recency_weighted: weighted(rows, "fantasy_average", recency),
    average_rating_recency_weighted: weighted(rows, "average_rating", recency),
    goals_per_appearance: total ? sum("goals_scored") / total : null,
    goals_conceded_per_appearance: total ? sum("goals_conceded") / total : null,
    penalties_saved_per_appearance: total ? sum("penalties_saved") / total : null,
    assists_per_appearance: total ? sum("assists") / total : null,
    bonus_events_per_appearance: total ? (sum("goals_scored") + sum("assists") + sum("penalties_saved")) / total : null,
    malus_events_per_appearance: total ? (sum("yellow_cards") + sum("red_cards") + sum("own_goals") + sum("penalties_missed") + sum("goals_conceded")) / total : null,
    continuity: request.selected_seasons.filter((season) => (rows.find((row) => row.season === season)?.rated_appearances ?? 0) >= request.continuity_threshold).length / request.selected_seasons.length,
    fantasy_average_volatility: volatility,
    latest_fantasy_average: latest?.fantasy_average ?? null,
    fantasy_average_trend_slope: slope,
    fantasy_average_absolute_change: latest?.fantasy_average !== null && previous?.fantasy_average !== null && latest && previous ? latest.fantasy_average! - previous.fantasy_average! : null,
    reliability_score: 100 * (0.5 * sample + 0.25 * coverage + 0.25 * recent)
  };
}

function percentiles(values: Array<[number, number]>, lower: boolean) {
  const sorted = [...values].sort((a, b) => a[1] - b[1]);
  const output = new Map<number, number>();
  let index = 0;
  while (index < sorted.length) {
    let end = index + 1;
    while (end < sorted.length && sorted[end][1] === sorted[index][1]) end++;
    const average = (index + end - 1) / 2;
    let value = sorted.length === 1 ? 100 : average / (sorted.length - 1) * 100;
    if (lower) value = 100 - value;
    for (let cursor = index; cursor < end; cursor++) output.set(sorted[cursor][0], value);
    index = end;
  }
  return output;
}

export async function staticRanking(request: RankingRequest): Promise<RankingResponse> {
  const data = await snapshot();
  const active = Object.entries(request.metric_weights).filter(([, weight]) => weight > 0);
  if (!active.length) throw new Error("È richiesto almeno un peso maggiore di zero");
  const pool = (currentListStore.get()?.items ?? data.current_list).filter((item) => item.classic_role === request.role).map((item) => data.details[String(item.player_id)]).filter((detail): detail is PlayerDetail => Boolean(detail?.history.length));
  const calculated = pool.map((detail) => ({ detail, values: metrics(detail.history, request) })).filter((row) => row.values.total_pv >= request.minimum_appearances);
  const excluded = calculated.filter((row) => active.some(([key]) => (row.values as Record<string, number | null>)[key] == null));
  const eligible = calculated.filter((row) => !excluded.includes(row));
  const metricPercentiles = Object.fromEntries(active.map(([key]) => [key, percentiles(eligible.map((row) => [row.detail.id, Number((row.values as Record<string, number | null>)[key])]), data.ranking_metadata.metrics.find((item) => item.key === key)?.direction === "lower")]));
  const weightTotal = active.reduce((sum, [, weight]) => sum + weight, 0);
  const items = eligible.map(({ detail, values }) => {
    const components = Object.fromEntries(active.map(([key, weight]) => {
      const percentile = metricPercentiles[key].get(detail.id)!;
      return [key, { value: Number((values as Record<string, number | null>)[key]), percentile, weight, contribution: percentile * weight / weightTotal, direction: data.ranking_metadata.metrics.find((item) => item.key === key)?.direction ?? "higher" }];
    }));
    return { position: 0, player_id: detail.id, display_name: detail.display_name, score: Object.values(components).reduce((sum, component) => sum + component.contribution, 0), reliability_score: values.reliability_score, total_pv: values.total_pv, seasons_with_pv: values.seasons_with_pv, fantasy_average_trend_slope: values.fantasy_average_trend_slope, fantasy_average_absolute_change: values.fantasy_average_absolute_change, metrics: components };
  }).sort((a, b) => b.score - a.score || a.display_name.localeCompare(b.display_name, "it"));
  items.forEach((item, index) => { item.position = index + 1; });
  return { configuration: request, initial_pool_size: calculated.length, eligible_pool_size: eligible.length, excluded: excluded.map(({ detail, values }) => ({ player_id: detail.id, display_name: detail.display_name, missing_metrics: active.filter(([key]) => (values as Record<string, number | null>)[key] == null).map(([key]) => key) })), items } as RankingResponse;
}

const CONFIG_KEY = "fantastat-ranking-configs";
export const staticApi = {
  seasons: async () => (await snapshot()).seasons,
  currentList: staticCurrentList,
  players: staticPlayers,
  player: staticPlayer,
  comparePlayers: staticCompare,
  rankingMetadata: async () => (await snapshot()).ranking_metadata,
  calculateRanking: staticRanking,
  rankingConfigs: async (): Promise<RankingConfig[]> => JSON.parse(localStorage.getItem(CONFIG_KEY) ?? "[]"),
  saveRankingConfig: async (name: string, configuration: RankingRequest): Promise<RankingConfig> => {
    const configs: RankingConfig[] = JSON.parse(localStorage.getItem(CONFIG_KEY) ?? "[]");
    const saved = { id: Math.max(0, ...configs.map((item) => item.id)) + 1, name, role: configuration.role, configuration };
    localStorage.setItem(CONFIG_KEY, JSON.stringify([...configs, saved]));
    return saved;
  },
  deleteRankingConfig: async (id: number) => {
    const configs: RankingConfig[] = JSON.parse(localStorage.getItem(CONFIG_KEY) ?? "[]");
    localStorage.setItem(CONFIG_KEY, JSON.stringify(configs.filter((item) => item.id !== id)));
  }
};
