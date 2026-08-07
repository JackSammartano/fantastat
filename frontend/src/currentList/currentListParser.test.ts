import { beforeEach, describe, expect, it, vi } from "vitest";
import readXlsxFile from "read-excel-file/browser";
import { parseCurrentListFile, reconcileCurrentList, type CurrentListDraft } from "./currentListParser";
import type { CurrentListItem } from "../models/api";

vi.mock("read-excel-file/browser", () => ({ default: vi.fn() }));

const columns = ["Id", "R", "RM", "Nome", "Squadra", "Qt.A", "Qt.I", "Diff.", "Qt.A M", "Qt.I M", "Diff.M", "FVM", "FVM M"];
const player = (id = 10, role = "C", current = 12, initial = 10, difference = 2) => [id, role, "C", "Calciatore", "Inter", current, initial, difference, current, initial, difference, 80, 80];
const file = { name: "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx", arrayBuffer: async () => new ArrayBuffer(2) } as File;
const row = { external_player_id: "10", name: "Calciatore", classic_role: "C" as const, mantra_roles: ["C"], team: "Inter", quotation: 12, initial_quotation: 10, quotation_change: 2, mantra_quotation: 12, initial_mantra_quotation: 10, mantra_quotation_change: 2, fvm: 80, fvm_mantra: 80 };
const draft: CurrentListDraft = { season: "2026/2027", fileName: "listone.xlsx", fileHash: "hash", importedAt: "2026-08-07", rows: [row] };

beforeEach(() => {
  vi.mocked(readXlsxFile).mockReset();
  vi.stubGlobal("crypto", { subtle: { digest: async () => new Uint8Array([1, 2]).buffer } });
});

describe("parseCurrentListFile", () => {
  it("legge soltanto Tutti, riconosce stagione e valori ufficiali", async () => {
    vi.mocked(readXlsxFile).mockResolvedValue([{ sheet: "Ceduti", data: [[999, "A"]] }, { sheet: "Tutti", data: [["Quotazioni Fantacalcio Stagione 2026 27"], columns, player()] }] as never);
    const result = await parseCurrentListFile(file);
    expect(result.season).toBe("2026/2027");
    expect(result.rows).toHaveLength(1);
    expect(result.rows[0]).toMatchObject({ external_player_id: "10", quotation: 12, initial_quotation: 10, quotation_change: 2 });
  });

  it("rifiuta un file senza foglio Tutti", async () => {
    vi.mocked(readXlsxFile).mockResolvedValue([{ sheet: "Ceduti", data: [] }] as never);
    await expect(parseCurrentListFile(file)).rejects.toThrow("Foglio 'Tutti' non trovato");
  });

  it("rifiuta variazioni incoerenti, ID duplicati e ruoli sconosciuti", async () => {
    vi.mocked(readXlsxFile).mockResolvedValue([{ sheet: "Tutti", data: [["Quotazioni Fantacalcio Stagione 2026 27"], columns, player(10, "C", 12, 10, 1)] }] as never);
    await expect(parseCurrentListFile(file)).rejects.toThrow("Variazione incoerente");
    vi.mocked(readXlsxFile).mockResolvedValue([{ sheet: "Tutti", data: [["Quotazioni Fantacalcio Stagione 2026 27"], columns, player(), player()] }] as never);
    await expect(parseCurrentListFile(file)).rejects.toThrow("ID duplicato");
    vi.mocked(readXlsxFile).mockResolvedValue([{ sheet: "Tutti", data: [["Quotazioni Fantacalcio Stagione 2026 27"], columns, player(10, "X")] }] as never);
    await expect(parseCurrentListFile(file)).rejects.toThrow("Ruolo non valido");
  });
});

describe("reconcileCurrentList", () => {
  it("mantiene il player id e lo storico dei giocatori già conosciuti", () => {
    const existing = [{ ...row, id: 4, player_id: 7, mapping_status: "certain_external_id", historical_seasons: 3 }] as CurrentListItem[];
    expect(reconcileCurrentList(draft, existing).items[0]).toMatchObject({ player_id: 7, historical_seasons: 3, quotation: 12 });
  });
  it("crea un profilo locale senza storico per un nuovo ID", () => {
    expect(reconcileCurrentList(draft, []).items[0]).toMatchObject({ player_id: -10, mapping_status: "new_player", historical_seasons: 0 });
  });
  it("esclude gli usciti perché ricostruisce il listone dal nuovo foglio Tutti", () => {
    const old = [{ ...row, external_player_id: "99", id: 99, player_id: 99, mapping_status: "certain_external_id", historical_seasons: 2 }] as CurrentListItem[];
    expect(reconcileCurrentList(draft, old).items.map((item) => item.external_player_id)).toEqual(["10"]);
  });
});
