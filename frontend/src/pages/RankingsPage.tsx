import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { StatePanel } from "../components/StatePanel";
import type {
  RankingMetadata,
  RankingConfig,
  RankingRequest,
  RankingResponse,
  Role,
  Season
} from "../models/api";
import { formatNumber } from "../utils/format";

const METRIC_LABELS: Record<string, string> = {
  fantasy_average_recency_weighted: "Fantamedia recente ponderata",
  average_rating_recency_weighted: "Media voto recente ponderata",
  goals_per_appearance: "Gol per presenza",
  goals_conceded_per_appearance: "Gol subiti per presenza",
  penalties_saved_per_appearance: "Rigori parati per presenza",
  assists_per_appearance: "Assist per presenza",
  bonus_events_per_appearance: "Bonus per presenza",
  malus_events_per_appearance: "Malus per presenza",
  continuity: "Continuità",
  fantasy_average_volatility: "Volatilità fantamedia",
  latest_fantasy_average: "Fantamedia ultima stagione",
  reliability_score: "Affidabilità del campione"
};

export function RankingsPage() {
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [metadata, setMetadata] = useState<RankingMetadata | null>(null);
  const [role, setRole] = useState<Role>("P");
  const [selectedSeasons, setSelectedSeasons] = useState<string[]>([]);
  const [minimumAppearances, setMinimumAppearances] = useState(10);
  const [decay, setDecay] = useState(0.75);
  const [continuityThreshold, setContinuityThreshold] = useState(19);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [result, setResult] = useState<RankingResponse | null>(null);
  const [configs, setConfigs] = useState<RankingConfig[]>([]);
  const [configName, setConfigName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.seasons(), api.rankingMetadata(), api.rankingConfigs()])
      .then(([seasonRows, metricRows, savedConfigs]) => {
        setSeasons(seasonRows);
        setSelectedSeasons(seasonRows.map((season) => season.code));
        setMetadata(metricRows);
        setWeights(
          Object.fromEntries(metricRows.metrics.map((metric) => [metric.key, 0]))
        );
        setConfigs(savedConfigs);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Errore API")
      )
      .finally(() => setLoading(false));
  }, []);

  const currentConfiguration = (): RankingRequest => ({
    role,
    selected_seasons: selectedSeasons,
    minimum_appearances: minimumAppearances,
    recency_decay: decay,
    continuity_threshold: continuityThreshold,
    metric_weights: weights
  });

  const calculate = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(
        await api.calculateRanking(currentConfiguration())
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Errore API");
    } finally {
      setLoading(false);
    }
  };

  if (!metadata && loading) {
    return <StatePanel title="Caricamento" message="Lettura metriche disponibili…" />;
  }
  if (!metadata) {
    return <StatePanel title="Classifiche non disponibili" message={error ?? "Configurazione assente"} tone="error" />;
  }

  const activeWeightCount = Object.values(weights).filter((weight) => weight > 0).length;
  const loadConfig = (config: RankingConfig) => {
    const value = config.configuration;
    setRole(value.role);
    setSelectedSeasons(value.selected_seasons);
    setMinimumAppearances(value.minimum_appearances);
    setDecay(value.recency_decay);
    setContinuityThreshold(value.continuity_threshold);
    setWeights(value.metric_weights);
    setResult(null);
  };
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Ranking trasparente</span>
          <h1>Classifiche personalizzate</h1>
          <p>
            Scegli tu i pesi. Ogni contributo è espresso come percentile nel
            gruppo filtrato e resta ispezionabile.
          </p>
        </div>
      </header>

      <section className="ranking-config">
        <div className="saved-configs">
          <label className="field">
            <span>Configurazioni salvate</span>
            <select
              defaultValue=""
              onChange={(event) => {
                const config = configs.find(
                  (item) => item.id === Number(event.target.value)
                );
                if (config) loadConfig(config);
              }}
            >
              <option value="">Seleziona…</option>
              {configs.map((config) => (
                <option value={config.id} key={config.id}>
                  {config.name} · {config.role}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Nome nuova configurazione</span>
            <input
              value={configName}
              maxLength={150}
              onChange={(event) => setConfigName(event.target.value)}
              placeholder="Es. Centrocampisti equilibrati"
            />
          </label>
          <button
            className="button button--secondary"
            type="button"
            disabled={
              !configName.trim() ||
              activeWeightCount === 0 ||
              selectedSeasons.length === 0
            }
            onClick={async () => {
              try {
                const saved = await api.saveRankingConfig(
                  configName.trim(),
                  currentConfiguration()
                );
                setConfigs((current) =>
                  [...current, saved].sort((a, b) => a.name.localeCompare(b.name))
                );
                setConfigName("");
              } catch (reason) {
                setError(reason instanceof Error ? reason.message : "Errore API");
              }
            }}
          >
            Salva
          </button>
        </div>
        {configs.length > 0 && (
          <div className="saved-config-list">
            {configs.map((config) => (
              <span key={config.id}>
                {config.name}
                <button
                  type="button"
                  aria-label={`Elimina ${config.name}`}
                  onClick={async () => {
                    try {
                      await api.deleteRankingConfig(config.id);
                      setConfigs((current) =>
                        current.filter((item) => item.id !== config.id)
                      );
                    } catch (reason) {
                      setError(
                        reason instanceof Error ? reason.message : "Errore API"
                      );
                    }
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="ranking-controls">
          <label className="field">
            <span>Ruolo</span>
            <select
              value={role}
              onChange={(event) => {
                const nextRole = event.target.value as Role;
                setRole(nextRole);
                setWeights((current) =>
                  Object.fromEntries(
                    Object.entries(current).map(([key, value]) => {
                      const metric = metadata.metrics.find(
                        (item) => item.key === key
                      );
                      return [
                        key,
                        metric?.roles.includes(nextRole) ? value : 0
                      ];
                    })
                  )
                );
              }}
            >
              <option value="P">Portieri</option>
              <option value="D">Difensori</option>
              <option value="C">Centrocampisti</option>
              <option value="A">Attaccanti</option>
            </select>
          </label>
          <label className="field">
            <span>Presenze minime totali</span>
            <input type="number" min="0" max="152" value={minimumAppearances} onChange={(event) => setMinimumAppearances(Number(event.target.value))} />
          </label>
          <label className="field">
            <span>Decadimento stagionale</span>
            <input type="number" min="0.01" max="1" step="0.05" value={decay} onChange={(event) => setDecay(Number(event.target.value))} />
          </label>
          <label className="field">
            <span>Soglia continuità</span>
            <input type="number" min="0" max="38" value={continuityThreshold} onChange={(event) => setContinuityThreshold(Number(event.target.value))} />
          </label>
        </div>

        <fieldset className="season-selector">
          <legend>Stagioni considerate</legend>
          {seasons.map((season) => (
            <label key={season.id}>
              <input
                type="checkbox"
                checked={selectedSeasons.includes(season.code)}
                onChange={(event) =>
                  setSelectedSeasons((current) =>
                    event.target.checked
                      ? [...current, season.code].sort()
                      : current.filter((code) => code !== season.code)
                  )
                }
              />
              {season.code}
            </label>
          ))}
        </fieldset>

        <div className="weight-grid">
          {metadata.metrics
            .filter((metric) => metric.roles.includes(role))
            .map((metric) => (
            <label className="weight-field" key={metric.key}>
              <span>
                {METRIC_LABELS[metric.key] ?? metric.key}
                <small>{metric.direction === "higher" ? "↑ maggiore" : "↓ minore"}</small>
              </span>
              <input
                type="number"
                min="0"
                max="1000"
                step="0.5"
                value={weights[metric.key] ?? 0}
                onChange={(event) =>
                  setWeights((current) => ({
                    ...current,
                    [metric.key]: Number(event.target.value)
                  }))
                }
              />
            </label>
            ))}
        </div>

        <button
          className="button button--primary"
          type="button"
          disabled={loading || selectedSeasons.length === 0 || activeWeightCount === 0}
          onClick={() => void calculate()}
        >
          Calcola classifica
        </button>
        <small className="config-note">
          {activeWeightCount} metriche attive · nessun preset applicato
        </small>
      </section>

      {error && <StatePanel title="Calcolo non riuscito" message={error} tone="error" />}
      {loading && result && <StatePanel title="Calcolo" message="Normalizzazione del pool…" />}

      {!loading && result && (
        <section className="table-panel ranking-results">
          <div className="table-summary">
            <strong>{result.eligible_pool_size} giocatori classificati</strong>
            <span>
              Pool {result.initial_pool_size} · esclusi per dati mancanti {result.excluded.length}
            </span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Giocatore</th>
                  <th>Punteggio</th>
                  <th>Presenze</th>
                  <th>Affidabilità</th>
                  <th>Composizione</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => (
                  <tr key={item.player_id}>
                    <td>{item.position}</td>
                    <td><Link className="player-link" to={`/players/${item.player_id}`}><strong>{item.display_name}</strong></Link></td>
                    <td><strong>{formatNumber(item.score, 1)}</strong></td>
                    <td>{item.total_pv ?? "—"}</td>
                    <td>
                      {item.reliability_score === null ? "—" : (
                        <ReliabilityBadge
                          band={item.reliability_score < 40 ? "low" : item.reliability_score < 70 ? "medium" : "high"}
                          score={item.reliability_score}
                        />
                      )}
                    </td>
                    <td>
                      <details className="score-details">
                        <summary>Dettagli</summary>
                        {Object.entries(item.metrics).map(([key, component]) => (
                          <div key={key}>
                            <span>{METRIC_LABELS[key] ?? key}</span>
                            <small>
                              valore {formatNumber(component.value)} · percentile {formatNumber(component.percentile, 1)} · contributo {formatNumber(component.contribution, 1)}
                            </small>
                          </div>
                        ))}
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
