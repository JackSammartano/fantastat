import readXlsxFile, { type Row } from "read-excel-file/browser";
import type { Role } from "../models/api";
import type { MatchdayImport, MatchdayPlayerVote } from "./types";

const asNumber = (value: unknown) => typeof value === "number" ? value : Number(value) || 0;

export function detectMatchdayMetadata(fileName: string, title: string) {
  const matchdayMatch = title.match(/(\d{1,2})\s*[ªa]?\s*giornata/i) ?? fileName.match(/giornata[_\s-]*(\d{1,2})/i);
  const seasonMatch = fileName.match(/stagione[_\s-]*(\d{4})[_\s-]*(\d{2,4})/i);
  if (!matchdayMatch) throw new Error("Giornata non riconosciuta nel file");
  if (!seasonMatch) throw new Error("Stagione non riconosciuta nel nome del file");
  const endYear = seasonMatch[2].length === 2 ? `20${seasonMatch[2]}` : seasonMatch[2];
  return { season: `${seasonMatch[1]}/${endYear}`, matchday: Number(matchdayMatch[1]) };
}

async function sha256(file: File) {
  const hash = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(hash)).map((item) => item.toString(16).padStart(2, "0")).join("");
}

export async function parseMatchdayFile(file: File, requestedSource = "Fantacalcio"): Promise<MatchdayImport> {
  const sheets = await readXlsxFile(file);
  const selected = sheets.find((item) => item.sheet === requestedSource) ?? sheets[0];
  if (!selected) throw new Error("Il file non contiene fogli leggibili");
  const source = selected.sheet;
  const rows = selected.data;
  const title = String(rows[0]?.[0] ?? "");
  const { season, matchday } = detectMatchdayMetadata(file.name, title);
  let team = "";
  let ignoredNonPlayers = 0;
  const votes: MatchdayPlayerVote[] = [];
  for (const row of rows as Row[]) {
    const first = row[0];
    if (typeof first === "string" && row.slice(1).every((cell: unknown) => cell === null) && !first.match(/Voti |Solo su|QUESTO FILE|E' DA/)) team = first;
    if (typeof first === "number" && !["P", "D", "C", "A"].includes(String(row[1]))) { ignoredNonPlayers += 1; continue; }
    if (typeof first !== "number") continue;
    votes.push({ externalPlayerId: String(first), role: String(row[1]) as Role, name: String(row[2] ?? ""), team, vote: typeof row[3] === "number" ? row[3] : null,
      goalsScored: asNumber(row[4]), goalsConceded: asNumber(row[5]), penaltiesSaved: asNumber(row[6]), penaltiesScored: asNumber(row[7]), penaltiesMissed: asNumber(row[8]), ownGoals: asNumber(row[9]), yellowCards: asNumber(row[10]), redCards: asNumber(row[11]), assists: asNumber(row[12]) });
  }
  if (votes.length === 0) throw new Error("Nessun voto riconosciuto nel foglio selezionato");
  return { key: `${season}|${matchday}|${source}`, season, matchday, source, fileName: file.name, fileHash: await sha256(file), importedAt: new Date().toISOString(), ignoredNonPlayers, votes };
}
