import { afterEach, describe, expect, it, vi } from "vitest";
import { api, getCurrentList, getPlayers } from "./client";

describe("getPlayers", () => {
  afterEach(() => vi.restoreAllMocks());

  it("serializza i filtri verificati dall'API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          page: 1,
          page_size: 25,
          total_items: 0,
          total_pages: 0
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    await getPlayers({
      search: "Rossi",
      team: "Inter",
      role: "D",
      minAppearances: 10,
      minSeasons: 2
    });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("search=Rossi");
    expect(url).toContain("team=Inter");
    expect(url).toContain("role=D");
    expect(url).toContain("min_appearances=10");
    expect(url).toContain("min_seasons=2");
  });

  it("serializza più ID distinti per il confronto", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ players: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await api.comparePlayers([12, 34]);

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("ids=12&ids=34");
  });

  it("serializza filtri e ordinamento del listone corrente", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [], page: 1, page_size: 25, total_items: 0, total_pages: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await getCurrentList({ role: "A", team: "Roma", mappingStatus: "new_player", minQuotation: 5, sortBy: "fvm", sortOrder: "desc" });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("role=A");
    expect(url).toContain("team=Roma");
    expect(url).toContain("mapping_status=new_player");
    expect(url).toContain("min_quotation=5");
    expect(url).toContain("sort_by=fvm");
  });

  it("invia la configurazione ranking senza aggiungere pesi impliciti", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          configuration: {},
          initial_pool_size: 0,
          eligible_pool_size: 0,
          excluded: [],
          items: []
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    const payload = {
      role: "C" as const,
      selected_seasons: ["2025/2026"],
      minimum_appearances: 10,
      recency_decay: 0.75,
      continuity_threshold: 19,
      metric_weights: { continuity: 2 }
    };

    await api.calculateRanking(payload);

    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual(payload);
  });

  it("invia una decisione mapping esplicita con nota", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 4,
          status: "resolved",
          resolution: "new_player",
          resolved_player_id: 12
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    await api.resolveMapping(4, {
      resolution: "new_player",
      notes: "Omonimo verificato"
    });

    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "/player-mappings/4/resolve"
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      resolution: "new_player",
      notes: "Omonimo verificato"
    });
  });

  it("applica una fusione soltanto con il token di anteprima", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 1,
          review_id: 4,
          source_player_id: 10,
          target_player_id: 20,
          status: "applied",
          backup_path: "database/backups/test.db"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    const token = "a".repeat(64);

    await api.applyMerge(4, token, "Verificato");

    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      preview_token: token,
      notes: "Verificato"
    });
  });
});
