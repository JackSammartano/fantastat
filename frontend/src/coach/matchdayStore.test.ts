import { beforeEach, describe, expect, it } from "vitest";
import { IDBFactory } from "fake-indexeddb";
import { matchdayStore } from "./matchdayStore";
import type { MatchdayImport } from "./types";

const imported = (matchday: number, votes = 1): MatchdayImport => ({ key: `2026/2027|${matchday}|Fantacalcio`, season: "2026/2027", matchday, source: "Fantacalcio", fileName: `g${matchday}.xlsx`, fileHash: `hash-${matchday}`, importedAt: "2026-08-07", ignoredNonPlayers: 0, votes: Array.from({ length: votes }, (_, id) => ({ externalPlayerId: String(id), role: "C", name: `P${id}`, team: "Inter", vote: 6, goalsScored: 0, goalsConceded: 0, penaltiesSaved: 0, penaltiesScored: 0, penaltiesMissed: 0, ownGoals: 0, yellowCards: 0, redCards: 0, assists: 0 })) });

beforeEach(() => { Object.defineProperty(globalThis, "indexedDB", { value: new IDBFactory(), configurable: true }); });

describe("matchdayStore", () => {
  it("ordina le giornate e consente importazioni non consecutive", async () => {
    await matchdayStore.save(imported(2)); await matchdayStore.save(imported(10)); await matchdayStore.save(imported(5));
    expect((await matchdayStore.list()).map((item) => item.matchday)).toEqual([10, 5, 2]);
  });
  it("sostituisce la stessa chiave senza duplicarla", async () => {
    await matchdayStore.save(imported(5, 1)); await matchdayStore.save(imported(5, 3));
    const rows = await matchdayStore.list();
    expect(rows).toHaveLength(1); expect(rows[0].votes).toHaveLength(3);
  });
  it("elimina una singola giornata", async () => {
    const value = imported(3); await matchdayStore.save(value); await matchdayStore.remove(value.key);
    expect(await matchdayStore.list()).toEqual([]);
  });
});
