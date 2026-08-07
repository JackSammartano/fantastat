import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Link, useLocation, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { CurrentListFilters } from "../api/client";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { StatePanel } from "../components/StatePanel";
import type { PlayerDetail } from "../models/api";
import { formatNumber, formatPercent, trendDirection } from "../utils/format";

function trendLabel(value: number | null): string {
  if (value === null) return "Storico insufficiente";
  if (trendDirection(value) === 1) return "In crescita";
  if (trendDirection(value) === -1) return "In calo";
  return "Stabile";
}

export function PlayerDetailPage() {
  const { playerId } = useParams();
  const location = useLocation();
  const navigationState = location.state as {
    from?: string;
    rankingState?: unknown;
    listState?: { filters: CurrentListFilters; search: string; team: string };
  } | null;
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const id = Number(playerId);
    if (!Number.isInteger(id)) {
      setError("Identificativo giocatore non valido");
      return;
    }
    api
      .player(id)
      .then((response) => active && setPlayer(response))
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Errore API");
        }
      });
    return () => {
      active = false;
    };
  }, [playerId]);

  const chartData = useMemo(
    () =>
      player?.history.map((item) => ({
        season: item.season.replace("20", ""),
        mediaVoto: item.average_rating,
        fantamedia: item.fantasy_average,
        presenze: item.rated_appearances,
        gol: item.goals_scored,
        assist: item.assists
      })) ?? [],
    [player]
  );

  if (error) {
    return (
      <StatePanel title="Giocatore non disponibile" message={error} tone="error" />
    );
  }
  if (!player) {
    return <StatePanel title="Caricamento" message="Lettura dello storico…" />;
  }

  const metrics = player.metrics;
  const trend = metrics.fantasy_average_percentage_change;
  return (
    <div className="page">
      <Link
        className="back-link"
        to={
          navigationState?.from === "rankings"
            ? "/rankings"
            : "/current-list"
        }
        state={
          navigationState?.from === "rankings"
            ? { restoreRanking: navigationState.rankingState }
            : { restoreList: navigationState?.listState }
        }
      >
        ← Torna {navigationState?.from === "rankings" ? "alle classifiche" : "al listone"}
      </Link>
      <header className="player-hero">
        <div>
          <div className="player-hero__meta">
            <span className={`role-chip role-chip--${metrics.latest_role}`}>
              {metrics.latest_role ?? "?"}
            </span>
            <span>{metrics.latest_available_season ?? "Nessuna stagione"}</span>
          </div>
          <h1>{player.display_name}</h1>
          <p>
            ID sorgente {player.external_player_id ?? "—"} ·{" "}
            {metrics.available_seasons} stagioni disponibili
          </p>
        </div>
        <ReliabilityBadge
          band={metrics.reliability_band}
          score={metrics.reliability_score}
        />
      </header>

      {player.current_list && (
        <section className="panel current-player-panel">
          <div className="panel__header">
            <div><span className="eyebrow">Listone ufficiale 2026/2027</span><h2>{player.current_list.team} · {player.current_list.role}</h2></div>
            <Link to="/current-list">Apri listone</Link>
          </div>
          <div className="current-player-values">
            <div><span>Ruoli Mantra</span><strong>{player.current_list.mantra_roles.join(" · ")}</strong></div>
            <div><span>Quotazione Classic</span><strong>{formatNumber(player.current_list.quotation, 0)}</strong><small>iniziale {formatNumber(player.current_list.initial_quotation, 0)}</small></div>
            <div><span>Quotazione Mantra</span><strong>{formatNumber(player.current_list.mantra_quotation, 0)}</strong><small>iniziale {formatNumber(player.current_list.initial_mantra_quotation, 0)}</small></div>
            <div><span>FVM Classic</span><strong>{formatNumber(player.current_list.fvm, 0)}</strong></div>
            <div><span>FVM Mantra</span><strong>{formatNumber(player.current_list.fvm_mantra, 0)}</strong></div>
          </div>
        </section>
      )}

      <section className="metric-grid">
        <article className="metric-card">
          <span>Fantamedia ponderata</span>
          <strong>{formatNumber(metrics.fantasy_average_weighted)}</strong>
          <small>
            Recency {formatNumber(metrics.fantasy_average_recency_weighted)}
          </small>
        </article>
        <article className="metric-card">
          <span>Media voto ponderata</span>
          <strong>{formatNumber(metrics.average_rating_weighted)}</strong>
          <small>{metrics.total_pv} partite a voto</small>
        </article>
        <article className="metric-card">
          <span>Trend recente</span>
          <strong className={trend && trend > 0 ? "positive" : "negative"}>
            {trend !== null && trend > 0 ? "+" : ""}
            {formatNumber(trend)}%
          </strong>
          <small>ultima vs precedente disponibile</small>
        </article>
        <article className="metric-card">
          <span>Continuità</span>
          <strong>{formatPercent(metrics.continuity)}</strong>
          <small>stagioni con almeno 19 Pv</small>
        </article>
      </section>

      <section className="trend-grid" aria-label="Tendenza sulle stagioni">
        <article className="trend-card">
          <div>
            <span className="eyebrow">Tendenza complessiva</span>
            <h2>Fantamedia</h2>
          </div>
          <strong
            className={
              metrics.fantasy_average_trend_slope === null
                ? ""
                : trendDirection(metrics.fantasy_average_trend_slope) === 1
                  ? "positive"
                  : trendDirection(metrics.fantasy_average_trend_slope) === -1
                    ? "negative"
                    : ""
            }
          >
            {trendLabel(metrics.fantasy_average_trend_slope)}
          </strong>
          <p>
            {metrics.fantasy_average_trend_slope === null
              ? "Servono almeno due stagioni con partite a voto."
              : `${trendDirection(metrics.fantasy_average_trend_slope) === 1 ? "+" : ""}${formatNumber(metrics.fantasy_average_trend_slope, 2)} punti medi per stagione.`}
          </p>
        </article>
        <article className="trend-card">
          <div>
            <span className="eyebrow">Tendenza complessiva</span>
            <h2>Media voto</h2>
          </div>
          <strong
            className={
              metrics.average_rating_trend_slope === null
                ? ""
                : trendDirection(metrics.average_rating_trend_slope) === 1
                  ? "positive"
                  : trendDirection(metrics.average_rating_trend_slope) === -1
                    ? "negative"
                    : ""
            }
          >
            {trendLabel(metrics.average_rating_trend_slope)}
          </strong>
          <p>
            {metrics.average_rating_trend_slope === null
              ? "Servono almeno due stagioni con partite a voto."
              : `${trendDirection(metrics.average_rating_trend_slope) === 1 ? "+" : ""}${formatNumber(metrics.average_rating_trend_slope, 2)} punti medi per stagione.`}
          </p>
        </article>
        <aside className="trend-note">
          La tendenza usa tutte le stagioni disponibili ed è ponderata per le
          partite a voto. Descrive lo storico: non è una previsione della
          stagione 2026/2027.
        </aside>
      </section>

      <div className="chart-grid">
        <section className="panel chart-panel">
          <div className="panel__header">
            <div>
              <span className="eyebrow">Rendimento</span>
              <h2>Medie per stagione</h2>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#d9dfd6" />
              <XAxis dataKey="season" />
              <YAxis domain={["auto", "auto"]} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="fantamedia"
                name="Fantamedia"
                stroke="#155c3b"
                strokeWidth={3}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="mediaVoto"
                name="Media voto"
                stroke="#d77a32"
                strokeWidth={2}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </section>

        <section className="panel chart-panel">
          <div className="panel__header">
            <div>
              <span className="eyebrow">Produzione</span>
              <h2>Presenze, gol e assist</h2>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#d9dfd6" />
              <XAxis dataKey="season" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="presenze" name="Pv" fill="#155c3b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="gol" name="Gol" fill="#d77a32" radius={[4, 4, 0, 0]} />
              <Bar dataKey="assist" name="Assist" fill="#d7b432" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="table-panel">
        <div className="table-summary">
          <strong>Storico completo</strong>
          <span>Valori originali per stagione</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Stagione</th>
                <th>Ruolo</th>
                <th>Squadra</th>
                <th>Pv</th>
                <th>Mv</th>
                <th>Fm</th>
                <th>Gol</th>
                <th>Assist</th>
                <th>Amm</th>
              </tr>
            </thead>
            <tbody>
              {player.history.map((item) => (
                <tr key={item.season_id}>
                  <td>{item.season}</td>
                  <td>{item.role}</td>
                  <td>{item.teams.join(", ")}</td>
                  <td>{item.rated_appearances}</td>
                  <td>{formatNumber(item.average_rating)}</td>
                  <td>{formatNumber(item.fantasy_average)}</td>
                  <td>{item.goals_scored}</td>
                  <td>{item.assists}</td>
                  <td>{item.yellow_cards}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
