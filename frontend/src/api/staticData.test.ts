import { afterEach, describe, expect, it, vi } from "vitest";
import type { PlayerDetail, PlayerHistory } from "../models/api";
import { staticCurrentList, staticRanking } from "./staticData";

const history = (season: string, fm: number, pv: number): PlayerHistory => ({
  season_id: Number(season.slice(0, 4)), season, role: "C", mantra_roles: ["C"], teams: ["Inter"],
  rated_appearances: pv, average_rating: fm - 0.5, fantasy_average: fm,
  goals_scored: 2, goals_conceded: 0, penalties_saved: 0, penalties_taken: 0,
  penalties_scored: 0, penalties_missed: 0, assists: 2, yellow_cards: 1,
  red_cards: 0, own_goals: 0, quality_status: "valid", quality_notes: null
});

const detail = (id: number, name: string, values: number[]): PlayerDetail => ({
  id, display_name: name, normalized_name: name.toLowerCase(), external_provider: "fantacalcio",
  external_player_id: String(id), matching_status: "certain_external_id", manual_notes: null,
  aliases: [name], history: [history("2024/2025", values[0], 20), history("2025/2026", values[1], 25)],
  metrics: {} as PlayerDetail["metrics"],
  current_list: { role: "C", mantra_roles: ["C"], team: "Inter", quotation: 10,
    initial_quotation: 10, mantra_quotation: 10, initial_mantra_quotation: 10,
    fvm: 100, fvm_mantra: 100, mapping_status: "certain_external_id" }
});

describe("static Pages data", () => {
  afterEach(() => vi.restoreAllMocks());

  it("filtra il listone e calcola il ranking nel browser", async () => {
    const first = detail(1, "Crescente", [6, 7]);
    const second = detail(2, "Calante", [7, 6]);
    const current = [first, second].map((player) => ({
      id: player.id, player_id: player.id, external_player_id: String(player.id), name: player.display_name,
      classic_role: "C", mantra_roles: ["C"], team: "Inter", quotation: 10,
      initial_quotation: 10, quotation_change: 0, mantra_quotation: 10,
      initial_mantra_quotation: 10, mantra_quotation_change: 0, fvm: 100,
      fvm_mantra: 100, mapping_status: "certain_external_id", historical_seasons: 2
    }));
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      schema_version: 1, season: "2026/2027", seasons: [], current_list: current,
      players: [], details: { "1": first, "2": second }, ranking_metadata: {
        normalization: "percentile", metrics: [{ key: "fantasy_average_trend_slope", direction: "higher", roles: ["C"] }]
      }
    }), { status: 200, headers: { "Content-Type": "application/json" } }));

    expect((await staticCurrentList({ search: "Cresc" })).total_items).toBe(1);
    const result = await staticRanking({ role: "C", selected_seasons: ["2024/2025", "2025/2026"],
      minimum_appearances: 0, recency_decay: 0.75, continuity_threshold: 19,
      metric_weights: { fantasy_average_trend_slope: 1 } });
    expect(result.items.map((item) => item.display_name)).toEqual(["Crescente", "Calante"]);
    expect(result.items[0].metrics.fantasy_average_trend_slope.percentile).toBe(100);
  });
});
