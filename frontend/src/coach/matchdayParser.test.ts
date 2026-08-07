import { beforeEach, describe, expect, it, vi } from "vitest";
import readXlsxFile from "read-excel-file/browser";
import { detectMatchdayMetadata, parseMatchdayFile } from "./matchdayParser";

vi.mock("read-excel-file/browser", () => ({ default: vi.fn() }));
const file = { name: "Voti_Fantacalcio_Stagione_2025_26_Giornata_38.xlsx", arrayBuffer: async () => new ArrayBuffer(2) } as File;

beforeEach(() => {
  vi.mocked(readXlsxFile).mockReset();
  vi.stubGlobal("crypto", { subtle: { digest: async () => new Uint8Array([1, 2]).buffer } });
});

describe("detectMatchdayMetadata", () => {
  it("rileva stagione e giornata dal file reale", () => {
    expect(detectMatchdayMetadata(file.name, "Voti Fantacalcio 38ª giornata di campionato")).toEqual({ season: "2025/2026", matchday: 38 });
  });
  it("usa il nome file come fallback per la giornata", () => {
    expect(detectMatchdayMetadata("Voti_Stagione-2026-2027_Giornata-5.xlsx", "Voti ufficiali")).toEqual({ season: "2026/2027", matchday: 5 });
  });
  it("rifiuta metadati incompleti", () => {
    expect(() => detectMatchdayMetadata("voti.xlsx", "Voti ufficiali")).toThrow("Giornata non riconosciuta");
  });
});

describe("parseMatchdayFile", () => {
  it("legge la fonte richiesta, assegna la squadra ed esclude l'allenatore", async () => {
    vi.mocked(readXlsxFile).mockResolvedValue([{ sheet: "Fantacalcio", data: [
      ["Voti Fantacalcio 38ª giornata di campionato"], ["Atalanta"],
      [4, "P", "Portiere", 6, 0, 1, 1, 0, 0, 0, 1, 0, 0],
      [900, "ALL", "Allenatore", 6, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [5, "D", "Difensore", null, 1, 0, 0, 0, 0, 0, 0, 1, 1]
    ] }, { sheet: "Italia", data: [] }] as never);
    const result = await parseMatchdayFile(file);
    expect(result.votes).toHaveLength(2);
    expect(result.ignoredNonPlayers).toBe(1);
    expect(result.votes[0]).toMatchObject({ externalPlayerId: "4", team: "Atalanta", vote: 6, goalsConceded: 1, penaltiesSaved: 1 });
    expect(result.votes[1]).toMatchObject({ vote: null, goalsScored: 1, redCards: 1, assists: 1 });
  });

  it("rifiuta un foglio senza righe giocatore", async () => {
    vi.mocked(readXlsxFile).mockResolvedValue([{ sheet: "Fantacalcio", data: [["Voti Fantacalcio 38ª giornata di campionato"], ["Atalanta"]] }] as never);
    await expect(parseMatchdayFile(file)).rejects.toThrow("Nessun voto riconosciuto");
  });
});
