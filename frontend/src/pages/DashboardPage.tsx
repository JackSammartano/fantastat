import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { StatePanel } from "../components/StatePanel";
import type {
  DataQualityIssue,
  PendingMapping,
  PlayerPage,
  Season
} from "../models/api";
import { formatNumber } from "../utils/format";

interface DashboardData {
  seasons: Season[];
  players: PlayerPage;
  leaders: PlayerPage;
  issues: DataQualityIssue[];
  mappings: PendingMapping[];
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.seasons(),
      api.players({ pageSize: 1 }),
      api.players({
        pageSize: 5,
        sortBy: "fantasy_average",
        sortOrder: "desc",
        minAppearances: 10
      }),
      api.issues(),
      api.pendingMappings()
    ])
      .then(([seasons, players, leaders, issues, mappings]) => {
        if (active) setData({ seasons, players, leaders, issues, mappings });
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error ? reason.message : "Errore di caricamento"
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <StatePanel
        title="Backend non raggiungibile"
        message={`${error}. Avvia FastAPI su 127.0.0.1:8000.`}
        tone="error"
      />
    );
  }
  if (!data) {
    return (
      <StatePanel
        title="Caricamento dashboard"
        message="Lettura dei dati locali in corso…"
      />
    );
  }

  const warningCount = data.issues.filter(
    (issue) => issue.category === "data_quality"
  ).length;
  return (
    <div className="page">
      <header className="page-header page-header--hero">
        <div>
          <span className="eyebrow">Storico Serie A</span>
          <h1>La tua asta, con memoria.</h1>
          <p>
            Quattro stagioni normalizzate, confrontabili e sempre accompagnate
            dalla qualità del campione.
          </p>
        </div>
        <Link className="button button--primary" to="/players">
          Esplora giocatori
        </Link>
      </header>

      <section className="stat-grid" aria-label="Riepilogo">
        <article className="stat-card">
          <span>Giocatori</span>
          <strong>{data.players.total_items.toLocaleString("it-IT")}</strong>
          <small>identità storiche distinte</small>
        </article>
        <article className="stat-card">
          <span>Stagioni</span>
          <strong>{data.seasons.length}</strong>
          <small>{data.seasons.map((season) => season.code).join(" · ")}</small>
        </article>
        <article className="stat-card">
          <span>Mapping da rivedere</span>
          <strong>{data.mappings.length}</strong>
          <small>nessuna fusione automatica</small>
        </article>
        <article className="stat-card">
          <span>Warning dati</span>
          <strong>{warningCount}</strong>
          <small>record conservati e segnalati</small>
        </article>
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel__header">
            <div>
              <span className="eyebrow">Ultima stagione disponibile</span>
              <h2>Fantamedia in evidenza</h2>
            </div>
            <Link to="/players">Vedi tutti</Link>
          </div>
          <div className="leader-list">
            {data.leaders.items.map((player, index) => (
              <Link
                className="leader-row"
                to={`/players/${player.id}`}
                key={player.id}
              >
                <span className="leader-row__rank">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div className="leader-row__identity">
                  <strong>{player.display_name}</strong>
                  <span>
                    {player.latest_role} · {player.latest_team}
                  </span>
                </div>
                <div className="leader-row__meta">
                  <strong>{player.latest_rated_appearances} Pv</strong>
                  <ReliabilityBadge
                    band={player.reliability_band}
                    score={player.reliability_score}
                  />
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="panel panel--accent">
          <span className="eyebrow">Metodo</span>
          <h2>Rendimento e affidabilità restano separati.</h2>
          <p>
            Una fantamedia alta su poche partite non viene nascosta né
            promossa: mostriamo il dato e, accanto, la solidità del campione.
          </p>
          <div className="method-metric">
            <span>Soglia continuità</span>
            <strong>19 presenze</strong>
          </div>
          <div className="method-metric">
            <span>Peso stagione precedente</span>
            <strong>{formatNumber(0.75, 2)}</strong>
          </div>
        </section>
      </div>
    </div>
  );
}

