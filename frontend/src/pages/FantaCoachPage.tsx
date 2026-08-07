import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { useCoach } from "../coach/CoachContext";
import { parseMatchdayFile } from "../coach/matchdayParser";
import { matchdayStore } from "../coach/matchdayStore";
import type { MatchdayImport, WatchPriority } from "../coach/types";
import type { Role } from "../models/api";
import { formatNumber } from "../utils/format";
import { calculateMatchdayTrend, type MatchdayTrend } from "../coach/matchdayTrend";
import { currentListStore, type ImportedCurrentList } from "../currentList/currentListStore";

type Tab = "targets" | "squad" | "matchdays";
const ROLES: Role[] = ["P", "D", "C", "A"];
const ROLE_LABELS: Record<Role, string> = { P: "Portieri", D: "Difensori", C: "Centrocampisti", A: "Attaccanti" };
const PRIORITIES: Record<WatchPriority, string> = { high: "Priorità alta", alternative: "Alternativa", bet: "Scommessa" };

export function FantaCoachPage() {
  const location = useLocation();
  const coach = useCoach();
  const restoredTab = (location.state as { restoreCoachTab?: Tab } | null)?.restoreCoachTab;
  const [tab, setTab] = useState<Tab>(restoredTab ?? "squad");
  const [imports, setImports] = useState<MatchdayImport[]>([]);
  const [preview, setPreview] = useState<MatchdayImport | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [selectedImportKey, setSelectedImportKey] = useState("");
  const refresh = () => matchdayStore.list().then(setImports).catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Archivio non disponibile"));
  useEffect(() => { void refresh(); }, []);
  useEffect(() => { if (restoredTab) setTab(restoredTab); }, [restoredTab, location.key]);

  const spent = coach.squad.reduce((sum, item) => sum + item.purchasePrice, 0);
  const selectedImport = selectedImportKey ? imports.find((item) => item.key === selectedImportKey) : null;
  const activeDataset = selectedImport ?? imports[0];
  const squadPerformance = useMemo(() => {
    const historyImports = !activeDataset ? [] : imports.filter((item) => item.season === activeDataset.season && item.source === activeDataset.source && (!selectedImport || item.matchday <= selectedImport.matchday));
    const relevantImports = selectedImport ? [selectedImport] : historyImports;
    return coach.squad.map((entry) => {
      const votes = relevantImports.flatMap((item) => item.votes.filter((vote) => vote.externalPlayerId === entry.player.externalPlayerId));
      const trendRows = historyImports.map((item) => ({ matchday: item.matchday, vote: item.votes.find((vote) => vote.externalPlayerId === entry.player.externalPlayerId)?.vote ?? null }));
      const rated = votes.filter((vote) => vote.vote !== null);
      return { entry, appearances: rated.length, average: rated.length ? rated.reduce((sum, vote) => sum + (vote.vote ?? 0), 0) / rated.length : null,
        goals: votes.reduce((sum, vote) => sum + vote.goalsScored, 0), assists: votes.reduce((sum, vote) => sum + vote.assists, 0),
        goalsConceded: votes.reduce((sum, vote) => sum + vote.goalsConceded, 0), penaltiesSaved: votes.reduce((sum, vote) => sum + vote.penaltiesSaved, 0),
        yellowCards: votes.reduce((sum, vote) => sum + vote.yellowCards, 0), redCards: votes.reduce((sum, vote) => sum + vote.redCards, 0), trend: calculateMatchdayTrend(trendRows) };
    });
  }, [coach.squad, imports, selectedImport, activeDataset]);

  const readFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setReading(true); setMessage(null); setPreview(null);
    try { setPreview(await parseMatchdayFile(file)); }
    catch (error) { setMessage(error instanceof Error ? error.message : "File non leggibile"); }
    finally { setReading(false); event.target.value = ""; }
  };

  const downloadBackup = () => {
    const backup = JSON.stringify({ version: 1, coach: JSON.parse(coach.exportBackup()), matchdays: imports, currentList: currentListStore.get() }, null, 2);
    const url = URL.createObjectURL(new Blob([backup], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "fantalab-allenatore-backup.json"; anchor.click(); URL.revokeObjectURL(url);
  };
  const importBackup = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as { version: number; coach: unknown; matchdays?: MatchdayImport[]; currentList?: ImportedCurrentList | null };
      if (parsed.version !== 1 || !parsed.coach) throw new Error("Backup Fanta-Allenatore non valido");
      coach.importBackup(JSON.stringify(parsed.coach));
      for (const item of parsed.matchdays ?? []) await matchdayStore.save(item);
      if (parsed.currentList) currentListStore.save(parsed.currentList);
      await refresh();
      setMessage("Backup completo ripristinato.");
    }
    catch (error) { setMessage(error instanceof Error ? error.message : "Backup non valido"); }
    finally { event.target.value = ""; }
  };

  return <div className="page">
    <header className="page-header"><div><span className="eyebrow">Area personale locale</span><h1>Fanta-Allenatore</h1><p>Obiettivi, rosa e giornate restano soltanto su questo dispositivo.</p></div><div className="coach-backup-actions"><button className="button button--ghost" onClick={downloadBackup}>Esporta backup</button><label className="button button--ghost file-button">Importa backup<input type="file" accept=".json" onChange={(event) => void importBackup(event)} /></label></div></header>
    <div className="coach-tabs" role="tablist">
      <button className={tab === "targets" ? "active" : ""} onClick={() => setTab("targets")}>Obiettivi <span>{coach.favorites.length}</span></button>
      <button className={tab === "squad" ? "active" : ""} onClick={() => setTab("squad")}>La mia rosa <span>{coach.squad.length}</span></button>
      <button className={tab === "matchdays" ? "active" : ""} onClick={() => setTab("matchdays")}>Giornate <span>{imports.length}</span></button>
    </div>

    {tab === "targets" && <section className="coach-section">
      <div className="coach-section__heading"><div><span className="eyebrow">Prima dell’asta</span><h2>Giocatori osservati</h2></div><Link className="button button--primary" to="/current-list">Aggiungi dal listone</Link></div>
      {coach.favorites.length === 0 ? <Empty title="Nessun obiettivo" text="Usa la stella nel listone o nella scheda di un giocatore." /> : <div className="coach-player-grid">{coach.favorites.map((favorite) => <article className="coach-player-card" key={favorite.player.id}>
        <PlayerHeading role={favorite.player.role} id={favorite.player.id} name={favorite.player.name} subtitle={`${favorite.player.team} · FVM ${formatNumber(favorite.player.fvm, 0)}`} onRemove={() => coach.toggleFavorite(favorite.player)} />
        <div className="coach-card-fields"><label className="field"><span>Priorità</span><select value={favorite.priority} onChange={(event) => coach.updateFavorite(favorite.player.id, { priority: event.target.value as WatchPriority })}>{Object.entries(PRIORITIES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="field"><span>Offerta massima</span><input type="number" min="0" value={favorite.maxBid ?? ""} onChange={(event) => coach.updateFavorite(favorite.player.id, { maxBid: event.target.value ? Number(event.target.value) : null })} /></label></div>
        <label className="field"><span>Nota</span><textarea value={favorite.note} onChange={(event) => coach.updateFavorite(favorite.player.id, { note: event.target.value })} placeholder="Perché seguirlo?" /></label>
        <button className="button button--secondary" onClick={() => coach.addToSquad(favorite.player)}>Segna come acquistato</button>
      </article>)}</div>}
    </section>}

    {tab === "squad" && <section className="coach-section">
      <div className="coach-budget"><label className="field"><span>Budget iniziale</span><input type="number" min="1" value={coach.settings.initialBudget} onChange={(event) => coach.updateSettings({ ...coach.settings, initialBudget: Number(event.target.value) })} /></label><BudgetValue label="Spesi" value={spent} /><BudgetValue label="Residui" value={coach.settings.initialBudget - spent} /><BudgetValue label="Giocatori" value={`${coach.squad.length}/25`} /></div>
      <div className="panel squad-view-controls"><h2>Rendimento della rosa <span>· {selectedImport ? `Giornata ${selectedImport.matchday}` : "Dati complessivi"}</span></h2><label className="field"><span>Vista</span><select value={selectedImportKey} onChange={(event) => setSelectedImportKey(event.target.value)}><option value="">Complessivo · tutte le giornate</option>{imports.map((item) => <option key={item.key} value={item.key}>{item.season} · Giornata {item.matchday} · {item.source}</option>)}</select></label>{imports.length === 0 && <button className="button button--primary" type="button" onClick={() => setTab("matchdays")}>Importa una giornata</button>}</div>
      {coach.squad.length === 0 ? <Empty title="Rosa ancora vuota" text="Aggiungi i giocatori acquistati dal listone o dagli obiettivi." /> : ROLES.map((role) => {
        const rows = squadPerformance.filter((row) => row.entry.player.role === role);
        if (rows.length === 0) return null;
        return <section className="table-panel squad-role-table" key={role}>
          <div className="table-summary"><div><span className={`role-chip role-chip--${role}`}>{role}</span><strong>{ROLE_LABELS[role]}</strong></div><span>{rows.length}/{coach.settings.roleLimits[role]} giocatori</span></div>
          <div className="table-scroll"><table><thead><tr>
            <th>Giocatore</th><th>Squadra</th><th>Prezzo</th><th>{selectedImport ? "Voto" : "Presenze"}</th>{!selectedImport && <th>Media voto</th>}<th>Forma 5</th><th>Trend recente</th>
            {role === "P" ? <><th>Gol subiti</th><th>Amm.</th><th>Esp.</th><th>Gol</th><th>Assist</th></> : <><th>Gol</th><th>Assist</th><th>Amm.</th><th>Esp.</th></>}<th></th>
          </tr></thead><tbody>{rows.map((row) => <tr key={row.entry.player.id}>
            <td><Link className="player-link" to={`/players/${row.entry.player.id}`} state={{ from: "coach", coachTab: "squad" }}><strong>{row.entry.player.name}</strong></Link></td><td>{row.entry.player.team}</td><td><input className="table-number-input" aria-label={`Prezzo ${row.entry.player.name}`} type="number" min="0" value={row.entry.purchasePrice} onChange={(event) => coach.updateSquadPlayer(row.entry.player.id, { purchasePrice: Number(event.target.value) })} /></td><td>{selectedImport ? formatNumber(row.average) : row.appearances}</td>{!selectedImport && <td>{formatNumber(row.average)}</td>}<td><span className="form-five"><strong>{formatNumber(row.trend.formAverage)}</strong><small>{row.trend.sampleSize} voti</small></span></td><td><TrendCell trend={row.trend} /></td>
            {role === "P" ? <><td>{row.goalsConceded}</td><td>{row.yellowCards}</td><td>{row.redCards}</td><td>{row.goals}</td><td>{row.assists}</td></> : <><td>{row.goals}</td><td>{row.assists}</td><td>{row.yellowCards}</td><td>{row.redCards}</td></>}<td><button className="table-remove" aria-label={`Rimuovi ${row.entry.player.name} dalla rosa`} onClick={() => coach.removeFromSquad(row.entry.player.id)}>×</button></td>
          </tr>)}</tbody></table></div>
        </section>;
      })}
    </section>}

    {tab === "matchdays" && <section className="coach-section">
      <div className="import-panel panel"><div><span className="eyebrow">Archivio privato</span><h2>Importa giornata</h2><p>Il file viene letto nel browser e non viene inviato né pubblicato.</p></div><label className="button button--primary file-button">{reading ? "Lettura…" : "Scegli Excel"}<input type="file" accept=".xlsx" disabled={reading} onChange={(event) => void readFile(event)} /></label></div>
      {message && <div className="mapping-warning">{message}</div>}
      {preview && <div className="panel import-preview"><h2>Anteprima importazione</h2><div className="stat-grid"><BudgetValue label="Stagione" value={preview.season} /><BudgetValue label="Giornata" value={preview.matchday} /><BudgetValue label="Fonte" value={preview.source} /><BudgetValue label="Calciatori" value={preview.votes.length} /></div>{preview.ignoredNonPlayers > 0 && <p>{preview.ignoredNonPlayers} righe allenatore riconosciute ed escluse correttamente.</p>}{imports.some((item) => item.key === preview.key) && <p className="mapping-warning">Giornata già presente: verrà sostituita.</p>}<div className="mapping-actions"><button className="button button--ghost" onClick={() => setPreview(null)}>Annulla</button><button className="button button--primary" onClick={async () => { await matchdayStore.save(preview); setPreview(null); await refresh(); }}>Conferma</button></div></div>}
      <div className="panel matchday-list"><div className="panel__header"><div><span className="eyebrow">Giornate importate</span><h2>{imports.length} importazioni</h2></div></div>{imports.length === 0 ? <p>Nessuna giornata importata.</p> : imports.map((item) => <div className="matchday-row" key={item.key}><div><strong>Giornata {item.matchday}</strong><span>{item.season} · {item.source} · {item.votes.length} calciatori</span></div><button className="button button--danger" onClick={async () => { await matchdayStore.remove(item.key); await refresh(); }}>Elimina</button></div>)}</div>
    </section>}

  </div>;
}

function Empty({ title, text }: { title: string; text: string }) { return <div className="panel coach-empty"><h2>{title}</h2><p>{text}</p></div>; }
function BudgetValue({ label, value }: { label: string; value: string | number }) { return <article className="stat-card"><span>{label}</span><strong>{value}</strong></article>; }
function PlayerHeading({ role, id, name, subtitle, onRemove }: { role: Role; id: number; name: string; subtitle: string; onRemove: () => void }) { return <div className="coach-player-card__head"><div><span className={`role-chip role-chip--${role}`}>{role}</span><Link to={`/players/${id}`} state={{ from: "coach", coachTab: "targets" }}><strong>{name}</strong><small>{subtitle}</small></Link></div><button aria-label={`Rimuovi ${name}`} onClick={onRemove}>×</button></div>; }
function TrendCell({ trend }: { trend: MatchdayTrend }) {
  if (trend.slope === null || trend.direction === null) return <span className="matchday-trend"><strong>—</strong><small>{trend.sampleSize < 3 ? "servono 3 voti" : "non disponibile"}</small></span>;
  const arrow = trend.direction === 1 ? "↑" : trend.direction === -1 ? "↓" : "→";
  return <span className={`matchday-trend matchday-trend--${trend.direction === 1 ? "up" : trend.direction === -1 ? "down" : "stable"}`}><strong>{arrow} {trend.slope > 0 ? "+" : ""}{formatNumber(trend.slope, 2)}/g</strong><small>{trend.sampleSize < 5 ? `${trend.sampleSize} voti · campione ridotto` : "ultimi 5 voti"}</small></span>;
}
