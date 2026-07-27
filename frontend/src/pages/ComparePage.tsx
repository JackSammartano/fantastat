import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { api } from "../api/client";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { StatePanel } from "../components/StatePanel";
import type { PlayerDetail, PlayerListItem } from "../models/api";
import { formatNumber, formatPercent } from "../utils/format";

export function ComparePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerListItem[]>([]);
  const [selected, setSelected] = useState<PlayerListItem[]>([]);
  const [players, setPlayers] = useState<PlayerDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const seasons = useMemo(
    () =>
      Array.from(
        new Set(players.flatMap((player) => player.history.map((row) => row.season)))
      ).sort(),
    [players]
  );
  const chartData = seasons.map((season) => {
    const row: Record<string, string | number | null> = { season };
    players.forEach((player) => {
      row[player.display_name] =
        player.history.find((item) => item.season === season)?.fantasy_average ??
        null;
    });
    return row;
  });

  const search = async () => {
    if (query.trim().length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.players({
        search: query.trim(),
        pageSize: 8,
        sortBy: "name"
      });
      setResults(response.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Errore API");
    } finally {
      setLoading(false);
    }
  };

  const compare = async () => {
    if (selected.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.comparePlayers(selected.map((item) => item.id));
      setPlayers(response.players);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Errore API");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Analisi affiancata</span>
          <h1>Confronto giocatori</h1>
          <p>Seleziona da due a quattro giocatori e confronta storico e campione.</p>
        </div>
      </header>

      <section className="compare-builder">
        <form
          className="compare-search"
          onSubmit={(event) => {
            event.preventDefault();
            void search();
          }}
        >
          <label className="field">
            <span>Cerca un giocatore</span>
            <input
              value={query}
              minLength={2}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Almeno due caratteri"
            />
          </label>
          <button className="button button--secondary" type="submit">
            Cerca
          </button>
        </form>

        {results.length > 0 && (
          <div className="search-results">
            {results.map((player) => {
              const alreadySelected = selected.some((item) => item.id === player.id);
              return (
                <button
                  type="button"
                  key={player.id}
                  disabled={alreadySelected || selected.length >= 4}
                  onClick={() => setSelected((current) => [...current, player])}
                >
                  <strong>{player.display_name}</strong>
                  <span>{player.latest_role} · {player.latest_team}</span>
                </button>
              );
            })}
          </div>
        )}

        <div className="selected-players">
          {selected.map((player) => (
            <button
              type="button"
              key={player.id}
              onClick={() => {
                setSelected((current) =>
                  current.filter((item) => item.id !== player.id)
                );
                setPlayers([]);
              }}
            >
              {player.display_name} ×
            </button>
          ))}
          <button
            className="button button--primary"
            type="button"
            disabled={selected.length < 2 || loading}
            onClick={() => void compare()}
          >
            Confronta
          </button>
        </div>
      </section>

      {error && <StatePanel title="Confronto non disponibile" message={error} tone="error" />}
      {loading && <StatePanel title="Caricamento" message="Preparazione confronto…" />}

      {!loading && players.length >= 2 && (
        <>
          <section className="comparison-grid">
            {players.map((player) => (
              <article className="comparison-card" key={player.id}>
                <span className={`role-chip role-chip--${player.metrics.latest_role}`}>
                  {player.metrics.latest_role ?? "?"}
                </span>
                <h2>{player.display_name}</h2>
                <ReliabilityBadge
                  band={player.metrics.reliability_band}
                  score={player.metrics.reliability_score}
                />
                <dl>
                  <div><dt>Fantamedia ponderata</dt><dd>{formatNumber(player.metrics.fantasy_average_weighted)}</dd></div>
                  <div><dt>Ultima fantamedia</dt><dd>{formatNumber(player.metrics.latest_fantasy_average)}</dd></div>
                  <div><dt>Media voto ponderata</dt><dd>{formatNumber(player.metrics.average_rating_weighted)}</dd></div>
                  <div><dt>Presenze totali</dt><dd>{player.metrics.total_pv}</dd></div>
                  <div><dt>Continuità</dt><dd>{formatPercent(player.metrics.continuity)}</dd></div>
                  <div><dt>Volatilità</dt><dd>{formatNumber(player.metrics.fantasy_average_volatility)}</dd></div>
                </dl>
              </article>
            ))}
          </section>

          <section className="panel chart-panel">
            <div className="panel__header">
              <div>
                <span className="eyebrow">Storico</span>
                <h2>Fantamedia per stagione</h2>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={340}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d9dfd6" />
                <XAxis dataKey="season" />
                <YAxis domain={["auto", "auto"]} />
                <Tooltip />
                <Legend />
                {players.map((player, index) => (
                  <Line
                    key={player.id}
                    type="monotone"
                    dataKey={player.display_name}
                    stroke={["#155c3b", "#d77a32", "#32709b", "#a34e76"][index]}
                    strokeWidth={3}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </section>
        </>
      )}
    </div>
  );
}
