import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type CurrentListFilters } from "../api/client";
import { StatePanel } from "../components/StatePanel";
import type { CurrentListPage, Role, Season } from "../models/api";
import { formatNumber } from "../utils/format";

const ROLES: Role[] = ["P", "D", "C", "A"];
const ROLE_NAMES: Record<Role, string> = {
  P: "Portieri",
  D: "Difensori",
  C: "Centrocampisti",
  A: "Attaccanti"
};

interface DashboardData {
  seasons: Season[];
  currentList: CurrentListPage;
  newPlayers: CurrentListPage;
  byRole: Record<Role, CurrentListPage>;
}

const listState = (filters: CurrentListFilters) => ({
  restoreList: { filters, search: "", team: "" }
});

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.seasons(),
      api.currentList({ pageSize: 5, sortBy: "fvm", sortOrder: "desc" }),
      api.currentList({ pageSize: 1, mappingStatus: "new_player" }),
      ...ROLES.map((role) =>
        api.currentList({ role, pageSize: 1, sortBy: "fvm", sortOrder: "desc" })
      )
    ])
      .then(([seasons, currentList, newPlayers, ...rolePages]) => {
        if (!active) return;
        setData({
          seasons,
          currentList,
          newPlayers,
          byRole: Object.fromEntries(
            ROLES.map((role, index) => [role, rolePages[index]])
          ) as Record<Role, CurrentListPage>
        });
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Errore di caricamento");
        }
      });
    return () => { active = false; };
  }, []);

  if (error) {
    return <StatePanel title="Dashboard non disponibile" message={error} tone="error" />;
  }
  if (!data) {
    return <StatePanel title="Caricamento dashboard" message="Preparazione del riepilogo asta…" />;
  }

  const historicalPlayers = data.currentList.total_items - data.newPlayers.total_items;
  const historicalSeasons = data.seasons.filter((season) => !season.is_current).length;

  return (
    <div className="page">
      <header className="page-header page-header--hero">
        <div>
          <span className="eyebrow">FantaLab · Asta 2026/2027</span>
          <h1>Il campo visivo sulla tua asta.</h1>
          <p>
            Listone ufficiale, valori d’asta e storico: tutto ciò che serve per
            individuare rapidamente i giocatori da seguire.
          </p>
        </div>
        <Link className="button button--primary" to="/current-list">
          Consulta il listone
        </Link>
      </header>

      <section className="stat-grid" aria-label="Riepilogo del listone">
        <article className="stat-card">
          <span>Giocatori disponibili</span>
          <strong>{data.currentList.total_items.toLocaleString("it-IT")}</strong>
          <small>nel listone ufficiale 26/27</small>
        </article>
        <article className="stat-card">
          <span>Con storico</span>
          <strong>{historicalPlayers.toLocaleString("it-IT")}</strong>
          <small>analizzabili sulle stagioni precedenti</small>
        </article>
        <article className="stat-card">
          <span>Nuovi profili</span>
          <strong>{data.newPlayers.total_items.toLocaleString("it-IT")}</strong>
          <small>senza uno storico collegato</small>
        </article>
        <article className="stat-card">
          <span>Profondità storica</span>
          <strong>{historicalSeasons}</strong>
          <small>stagioni precedenti disponibili</small>
        </article>
      </section>

      <section className="dashboard-section">
        <div className="dashboard-section__header">
          <div><span className="eyebrow">Composizione del listone</span><h2>Disponibilità per ruolo</h2></div>
          <span>{data.currentList.total_items} giocatori totali</span>
        </div>
        <div className="role-overview">
          {ROLES.map((role) => {
            const roleData = data.byRole[role];
            const topPlayer = roleData.items[0];
            const filters: CurrentListFilters = { role, page: 1, pageSize: 25, sortBy: "fvm", sortOrder: "desc" };
            return (
              <Link className="role-summary-card" key={role} to="/current-list" state={listState(filters)}>
                <div><span className={`role-chip role-chip--${role}`}>{role}</span><strong>{ROLE_NAMES[role]}</strong></div>
                <strong className="role-summary-card__count">{roleData.total_items}</strong>
                <small>{topPlayer ? `FVM più alto: ${topPlayer.name} · ${formatNumber(topPlayer.fvm, 0)}` : "Nessun giocatore"}</small>
              </Link>
            );
          })}
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel__header">
            <div><span className="eyebrow">Indicazioni d’asta</span><h2>Top FVM Classic</h2></div>
            <Link to="/current-list" state={listState({ page: 1, pageSize: 25, sortBy: "fvm", sortOrder: "desc" })}>Apri classifica</Link>
          </div>
          <div className="leader-list">
            {data.currentList.items.map((player, index) => (
              <Link className="leader-row" to={`/players/${player.player_id}`} state={{ from: "current-list", listState: listState({ page: 1, pageSize: 25, sortBy: "fvm", sortOrder: "desc" }).restoreList }} key={player.id}>
                <span className="leader-row__rank">{String(index + 1).padStart(2, "0")}</span>
                <div className="leader-row__identity"><strong>{player.name}</strong><span>{player.classic_role} · {player.team}</span></div>
                <div className="leader-row__meta"><strong>{formatNumber(player.fvm, 0)}</strong><span>su 1000</span></div>
              </Link>
            ))}
          </div>
        </section>

        <section className="panel panel--accent dashboard-actions">
          <span className="eyebrow">Accesso rapido</span>
          <h2>Prepara le tue scelte.</h2>
          <Link to="/current-list"><strong>Listone 26/27</strong><span>Filtra e consulta tutti i giocatori →</span></Link>
          <Link to="/rankings"><strong>Classifiche</strong><span>Crea graduatorie per ruolo →</span></Link>
          <Link to="/compare"><strong>Confronto</strong><span>Metti i candidati faccia a faccia →</span></Link>
        </section>
      </div>
    </div>
  );
}
