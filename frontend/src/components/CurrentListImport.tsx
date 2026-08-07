import { useState, type ChangeEvent } from "react";
import { api } from "../api/client";
import { useCoach } from "../coach/CoachContext";
import { parseCurrentListFile, reconcileCurrentList } from "../currentList/currentListParser";
import { currentListStore, type ImportedCurrentList } from "../currentList/currentListStore";
import type { CurrentListItem } from "../models/api";

interface Preview {
  data: ImportedCurrentList;
  added: number;
  removed: number;
  changed: number;
}

export function CurrentListImport({ onUpdated }: { onUpdated: () => void }) {
  const coach = useCoach();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<ImportedCurrentList | null>(() => currentListStore.get());
  const [preview, setPreview] = useState<Preview | null>(null);
  const [reading, setReading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadFullList = async (): Promise<CurrentListItem[]> => {
    const first = await api.currentList({ page: 1, pageSize: 100, sortBy: "name", sortOrder: "asc" });
    const items = [...first.items];
    for (let page = 2; page <= first.total_pages; page += 1) items.push(...(await api.currentList({ page, pageSize: 100, sortBy: "name", sortOrder: "asc" })).items);
    return items;
  };

  const readFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setOpen(true);
    setReading(true); setMessage(null); setPreview(null);
    try {
      const [draft, previous] = await Promise.all([parseCurrentListFile(file), loadFullList()]);
      const data = reconcileCurrentList(draft, previous);
      const before = new Map(previous.filter((item) => item.external_player_id).map((item) => [item.external_player_id!, item]));
      const afterIds = new Set(data.items.map((item) => item.external_player_id));
      setPreview({
        data,
        added: data.items.filter((item) => !before.has(item.external_player_id!)).length,
        removed: previous.filter((item) => item.external_player_id && !afterIds.has(item.external_player_id)).length,
        changed: data.items.filter((item) => { const old = before.get(item.external_player_id!); return old && (old.quotation !== item.quotation || old.team !== item.team || old.classic_role !== item.classic_role); }).length
      });
    } catch (error) { setMessage(error instanceof Error ? error.message : "Listone non leggibile"); }
    finally { setReading(false); event.target.value = ""; }
  };

  return <div className="current-list-import">
    <label className="button button--primary file-button">{reading ? "Lettura…" : "Aggiorna listone"}<input type="file" accept=".xlsx" disabled={reading} onChange={(event) => void readFile(event)} /></label>
    {open && <div className="current-list-import__content">
      <button className="button button--ghost current-list-import__close" type="button" onClick={() => setOpen(false)}>Chiudi</button>
      {reading && <div className="panel"><span className="eyebrow">Aggiornamento privato</span><h2>Lettura del listone…</h2><p>Il file viene elaborato soltanto in questo browser.</p></div>}
      {message && <div className="mapping-warning">{message}</div>}
      {preview && <div className="panel import-preview"><h2>Anteprima aggiornamento</h2><div className="stat-grid"><Value label="Stagione" value={preview.data.season} /><Value label="Calciatori" value={preview.data.items.length} /><Value label="Nuovi" value={preview.added} /><Value label="Usciti" value={preview.removed} /><Value label="Modificati" value={preview.changed} /></div>{active?.fileHash === preview.data.fileHash && <p className="mapping-warning">Questo stesso file è già stato importato.</p>}<div className="mapping-actions"><button className="button button--ghost" onClick={() => setPreview(null)}>Annulla</button><button className="button button--primary" onClick={() => { currentListStore.save(preview.data); coach.reconcileCurrentPlayers(preview.data.items); setActive(preview.data); setPreview(null); setMessage("Listone aggiornato correttamente."); onUpdated(); }}>Conferma aggiornamento</button></div></div>}
      {active && <div className="panel matchday-list"><div className="matchday-row"><div><strong>{active.fileName}</strong><span>{active.items.length} calciatori · importato il {new Date(active.importedAt).toLocaleString("it-IT")}</span></div><button className="button button--danger" onClick={() => { currentListStore.remove(); setActive(null); setMessage("Ripristinato il listone incluso nell'app."); onUpdated(); }}>Ripristina versione inclusa</button></div></div>}
    </div>}
  </div>;
}

function Value({ label, value }: { label: string; value: string | number }) { return <article className="stat-card"><span>{label}</span><strong>{value}</strong></article>; }
