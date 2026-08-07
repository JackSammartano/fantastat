import { beforeEach, describe, expect, it } from "vitest";
import { currentListStore, filterCurrentList, type ImportedCurrentList } from "./currentListStore";

const items = [
  { id: 1, player_id: 1, external_player_id: "1", name: "Alfa", classic_role: "A" as const, mantra_roles: ["Pc"], team: "Roma", quotation: 20, initial_quotation: 15, quotation_change: 5, mantra_quotation: null, initial_mantra_quotation: null, mantra_quotation_change: null, fvm: null, fvm_mantra: null, mapping_status: "certain_external_id", historical_seasons: 3 },
  { id: 2, player_id: 2, external_player_id: "2", name: "Beta", classic_role: "D" as const, mantra_roles: ["Dc"], team: "Inter", quotation: 5, initial_quotation: 7, quotation_change: -2, mantra_quotation: null, initial_mantra_quotation: null, mantra_quotation_change: null, fvm: null, fvm_mantra: null, mapping_status: "new_player", historical_seasons: 0 }
];
const value: ImportedCurrentList = { version: 1, season: "2026/2027", fileName: "listone.xlsx", fileHash: "hash", importedAt: "2026-08-07", items };

beforeEach(() => localStorage.clear());

describe("currentListStore", () => {
  it("salva, rilegge e ripristina il listone incluso", () => {
    currentListStore.save(value); expect(currentListStore.get()).toEqual(value);
    currentListStore.remove(); expect(currentListStore.get()).toBeNull();
  });
  it("ignora dati locali corrotti", () => {
    localStorage.setItem("fantalab-current-list-import", "{rotto");
    expect(currentListStore.get()).toBeNull();
  });
  it("applica insieme filtri, ordinamento e paginazione", () => {
    expect(filterCurrentList(items, { role: "A", sortBy: "quotation", sortOrder: "desc" }).items.map((item) => item.name)).toEqual(["Alfa"]);
    expect(filterCurrentList(items, { page: 2, pageSize: 1, sortBy: "quotation", sortOrder: "desc" }).items[0].name).toBe("Beta");
  });
});
