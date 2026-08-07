import readXlsxFile, { type Row } from "read-excel-file/browser";
import type { CurrentListItem, Role } from "../models/api";
import type { ImportedCurrentList } from "./currentListStore";

export interface CurrentListDraft {
  season: string;
  fileName: string;
  fileHash: string;
  importedAt: string;
  rows: Array<Omit<CurrentListItem, "id" | "player_id" | "mapping_status" | "historical_seasons">>;
}

const requiredHeaders = ["Id", "R", "RM", "Nome", "Squadra", "Qt.A", "Qt.I", "Diff."];
const numeric = (value: unknown, field: string) => {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) throw new Error(`Valore ${field} non valido`);
  return parsed;
};
const sha256 = async (file: File) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await file.arrayBuffer()))).map((item) => item.toString(16).padStart(2, "0")).join("");

export async function parseCurrentListFile(file: File): Promise<CurrentListDraft> {
  const sheets = await readXlsxFile(file);
  const sheet = sheets.find((item) => item.sheet.toLocaleLowerCase("it") === "tutti");
  if (!sheet) throw new Error("Foglio 'Tutti' non trovato");
  const title = String(sheet.data[0]?.[0] ?? "");
  const season = title.match(/Stagione\s+(\d{4})\s+(\d{2,4})/i);
  if (!season) throw new Error("Stagione non riconosciuta nel titolo del listone");
  const end = season[2].length === 2 ? `20${season[2]}` : season[2];
  const headerIndex = sheet.data.findIndex((row) => requiredHeaders.every((header) => row.includes(header)));
  if (headerIndex < 0) throw new Error("Intestazioni del listone non riconosciute");
  const headers = sheet.data[headerIndex].map(String);
  const column = (name: string) => headers.indexOf(name);
  const seen = new Set<string>();
  const rows = (sheet.data.slice(headerIndex + 1) as Row[]).filter((row) => typeof row[column("Id")] === "number").map((row) => {
    const externalPlayerId = String(row[column("Id")]);
    if (seen.has(externalPlayerId)) throw new Error(`ID duplicato nel foglio Tutti: ${externalPlayerId}`);
    seen.add(externalPlayerId);
    const role = String(row[column("R")]) as Role;
    if (!(["P", "D", "C", "A"] as string[]).includes(role)) throw new Error(`Ruolo non valido per ID ${externalPlayerId}`);
    const quotation = numeric(row[column("Qt.A")], "Qt.A");
    const initialQuotation = numeric(row[column("Qt.I")], "Qt.I");
    const declaredChange = numeric(row[column("Diff.")], "Diff.");
    if (quotation - initialQuotation !== declaredChange) throw new Error(`Variazione incoerente per ${String(row[column("Nome")])}`);
    return {
      external_player_id: externalPlayerId, name: String(row[column("Nome")] ?? "").trim(), classic_role: role,
      mantra_roles: String(row[column("RM")] ?? "").split(";").filter(Boolean), team: String(row[column("Squadra")] ?? "").trim(),
      quotation, initial_quotation: initialQuotation, quotation_change: declaredChange,
      mantra_quotation: column("Qt.A M") >= 0 ? numeric(row[column("Qt.A M")], "Qt.A M") : null,
      initial_mantra_quotation: column("Qt.I M") >= 0 ? numeric(row[column("Qt.I M")], "Qt.I M") : null,
      mantra_quotation_change: column("Diff.M") >= 0 ? numeric(row[column("Diff.M")], "Diff.M") : null,
      fvm: column("FVM") >= 0 ? numeric(row[column("FVM")], "FVM") : null,
      fvm_mantra: column("FVM M") >= 0 ? numeric(row[column("FVM M")], "FVM M") : null
    };
  });
  if (!rows.length) throw new Error("Nessun calciatore riconosciuto nel foglio Tutti");
  return { season: `${season[1]}/${end}`, fileName: file.name, fileHash: await sha256(file), importedAt: new Date().toISOString(), rows };
}

const syntheticId = (externalId: string) => -Math.max(1, Number(externalId) || Array.from(externalId).reduce((sum, char) => sum + char.charCodeAt(0), 0));

export function reconcileCurrentList(draft: CurrentListDraft, existing: CurrentListItem[]): ImportedCurrentList {
  const byExternalId = new Map(existing.filter((item) => item.external_player_id).map((item) => [item.external_player_id!, item]));
  return { version: 1, season: draft.season, fileName: draft.fileName, fileHash: draft.fileHash, importedAt: draft.importedAt, items: draft.rows.map((row) => {
    const previous = byExternalId.get(row.external_player_id!);
    const id = previous?.id ?? syntheticId(row.external_player_id!);
    return { ...row, id, player_id: previous?.player_id ?? id, mapping_status: previous?.mapping_status ?? "new_player", historical_seasons: previous?.historical_seasons ?? 0 };
  }) };
}
