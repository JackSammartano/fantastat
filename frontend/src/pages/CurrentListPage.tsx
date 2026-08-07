import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, type CurrentListFilters } from "../api/client";
import { StatePanel } from "../components/StatePanel";
import type { CurrentListPage as CurrentListData, Role } from "../models/api";

const number = (value: number | null) => value?.toLocaleString("it-IT") ?? "—";

export function CurrentListPage() {
  const location = useLocation();
  const restored = (location.state as {
    restoreList?: { filters: CurrentListFilters; search: string; team: string };
  } | null)?.restoreList;
  const [filters, setFilters] = useState<CurrentListFilters>(
    restored?.filters ?? { page: 1, pageSize: 25, sortBy: "quotation", sortOrder: "desc" }
  );
  const [search, setSearch] = useState(restored?.search ?? "");
  const [team, setTeam] = useState(restored?.team ?? "");
  const [data, setData] = useState<CurrentListData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    api.currentList(filters).then((result) => active && setData(result)).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "Errore API");
    });
    return () => { active = false; };
  }, [filters]);

  const update = (patch: Partial<CurrentListFilters>) => setFilters((current) => ({ ...current, ...patch, page: 1 }));

  return <div className="page">
    <header className="page-header">
      <div><span className="eyebrow">Asta 2026/2027</span><h1>Listone ufficiale</h1><p>Quotazioni, FVM, ruoli e collegamento con lo storico.</p></div>
    </header>
    <form className="filters current-list-filters" onSubmit={(event) => { event.preventDefault(); update({ search: search.trim() || undefined, team: team.trim() || undefined }); }}>
      <label className="field field--search"><span>Cerca</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Es. Dimarco" /></label>
      <label className="field"><span>Squadra</span><input value={team} onChange={(event) => setTeam(event.target.value)} placeholder="Es. Inter" /></label>
      <label className="field"><span>Ruolo</span><select value={filters.role ?? ""} onChange={(event) => update({ role: event.target.value as Role | "" })}><option value="">Tutti</option><option value="P">P</option><option value="D">D</option><option value="C">C</option><option value="A">A</option></select></label>
      <label className="field"><span>Identità</span><select value={filters.mappingStatus ?? ""} onChange={(event) => update({ mappingStatus: event.target.value as CurrentListFilters["mappingStatus"] })}><option value="">Tutte</option><option value="certain_external_id">Con storico</option><option value="new_player">Nuovi</option></select></label>
      <label className="field"><span>Ordina</span><select value={filters.sortBy} onChange={(event) => update({ sortBy: event.target.value })}><option value="quotation">Quotazione Classic</option><option value="mantra_quotation">Quotazione Mantra</option><option value="fvm">FVM Classic / 1000</option><option value="fvm_mantra">FVM Mantra / 1000</option><option value="name">Nome</option></select></label>
      <button className="button button--primary" type="submit">Applica</button>
      <button className="button button--ghost" type="button" onClick={() => { setSearch(""); setTeam(""); setFilters({ page: 1, pageSize: 25, sortBy: "quotation", sortOrder: "desc" }); }}>Azzera</button>
    </form>
    {error ? <StatePanel title="Errore di caricamento" message={error} tone="error" /> : !data ? <StatePanel title="Caricamento" message="Lettura del listone…" /> : data.items.length === 0 ? <StatePanel title="Nessun risultato" message="Modifica i filtri applicati." /> : <section className="table-panel">
      <div className="table-summary"><strong>{data.total_items.toLocaleString("it-IT")} calciatori</strong><span>Pagina {data.page} di {data.total_pages}</span></div>
      <div className="table-scroll"><table><thead><tr><th>Giocatore</th><th>Squadra</th><th title="Quotazione attuale Classic">Quotazione Classic</th><th title="Quotazione attuale Mantra">Quotazione Mantra</th><th title="FantaValore di Mercato Classic su budget 1000">FVM Classic / 1000</th><th title="FantaValore di Mercato Mantra su budget 1000">FVM Mantra / 1000</th><th>Storico</th></tr></thead><tbody>{data.items.map((item) => <tr key={item.id}>
        <td><Link className="player-link" to={`/players/${item.player_id}`} state={{ from: "current-list", listState: { filters, search, team } }}><span className={`role-chip role-chip--${item.classic_role}`}>{item.classic_role}</span><strong>{item.name}</strong></Link></td>
        <td>{item.team}</td><td>{number(item.quotation)}</td><td>{number(item.mantra_quotation)}</td><td>{number(item.fvm)}</td><td>{number(item.fvm_mantra)}</td><td>{item.historical_seasons ? `${item.historical_seasons}/4` : <span className="status-pill status-pill--new">Nuovo</span>}</td>
      </tr>)}</tbody></table></div>
      <div className="pagination"><button className="button button--ghost" disabled={data.page <= 1} onClick={() => setFilters((current) => ({ ...current, page: (current.page ?? 1) - 1 }))}>Precedente</button><span>{data.page}</span><button className="button button--ghost" disabled={data.page >= data.total_pages} onClick={() => setFilters((current) => ({ ...current, page: (current.page ?? 1) + 1 }))}>Successiva</button></div>
    </section>}
  </div>;
}
