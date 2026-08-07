import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
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
import { formatNumber, trendDirection } from "../utils/format";

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
  fantasy_average_trend_slope: "Trend fantamedia",
  reliability_score: "Affidabilità del campione"
};

interface RankingPreset {
  key: string;
  role: Role;
  name: string;
  description: string;
  minimumAppearances: number;
  weights: Record<string, number>;
}

interface RankingViewState {
  role: Role;
  selectedSeasons: string[];
  minimumAppearances: number;
  decay: number;
  continuityThreshold: number;
  weights: Record<string, number>;
  result: RankingResponse | null;
  presetKey: string;
}

const RANKING_PRESETS: RankingPreset[] = [
  {
    key: "p-equilibrato",
    role: "P",
    name: "Portiere equilibrato",
    description: "Premia rendimento, pochi gol subiti, continuità e solidità del campione.",
    minimumAppearances: 10,
    weights: { average_rating_recency_weighted: 2, goals_conceded_per_appearance: 3, penalties_saved_per_appearance: 1, continuity: 2, fantasy_average_volatility: 1, fantasy_average_trend_slope: 1, reliability_score: 1 }
  },
  {
    key: "d-bonus",
    role: "D",
    name: "Difensore da bonus",
    description: "Bilancia fantamedia, qualità del voto, bonus e presenza costante.",
    minimumAppearances: 10,
    weights: { fantasy_average_recency_weighted: 3, average_rating_recency_weighted: 2, goals_per_appearance: 1.5, assists_per_appearance: 1.5, continuity: 1, fantasy_average_trend_slope: 1.5, reliability_score: 1 }
  },
  {
    key: "c-offensivo",
    role: "C",
    name: "Centrocampista offensivo",
    description: "Dà priorità a fantamedia, gol e assist senza ignorare continuità e affidabilità.",
    minimumAppearances: 10,
    weights: { fantasy_average_recency_weighted: 3, goals_per_appearance: 2, assists_per_appearance: 2, bonus_events_per_appearance: 1, continuity: 1, fantasy_average_trend_slope: 1.5, reliability_score: 1 }
  },
  {
    key: "a-bonus",
    role: "A",
    name: "Attaccante da bonus",
    description: "Privilegia fantamedia, gol e produzione di bonus sul pool degli attaccanti attuali.",
    minimumAppearances: 8,
    weights: { fantasy_average_recency_weighted: 3, goals_per_appearance: 3, assists_per_appearance: 1, bonus_events_per_appearance: 2, continuity: 0.5, fantasy_average_trend_slope: 1, reliability_score: 0.5 }
  }
];

export function RankingsPage() {
  const location = useLocation();
  const restored = (
    location.state as { restoreRanking?: RankingViewState } | null
  )?.restoreRanking;
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
  const [presetKey, setPresetKey] = useState("p-equilibrato");

  useEffect(() => {
    Promise.all([api.seasons(), api.rankingMetadata(), api.rankingConfigs()])
      .then(([seasonRows, metricRows, savedConfigs]) => {
        setSeasons(seasonRows);
        setMetadata(metricRows);
        if (restored) {
          setRole(restored.role);
          setSelectedSeasons(restored.selectedSeasons);
          setMinimumAppearances(restored.minimumAppearances);
          setDecay(restored.decay);
          setContinuityThreshold(restored.continuityThreshold);
          setWeights(restored.weights);
          setResult(restored.result);
          setPresetKey(restored.presetKey);
        } else {
          setSelectedSeasons(
            seasonRows.filter((season) => !season.is_current).map((season) => season.code)
          );
          const preset = RANKING_PRESETS[0];
          setWeights(Object.fromEntries(metricRows.metrics.map((metric) => [metric.key, preset.weights[metric.key] ?? 0])));
          setMinimumAppearances(preset.minimumAppearances);
        }
        setConfigs(savedConfigs);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Errore API")
      )
      .finally(() => setLoading(false));
  }, [restored]);

  const currentConfiguration = (): RankingRequest => ({
    role,
    selected_seasons: selectedSeasons,
    minimum_appearances: minimumAppearances,
    recency_decay: decay,
    continuity_threshold: continuityThreshold,
    metric_weights: weights
  });

  const loadPreset = (key: string) => {
    const preset = RANKING_PRESETS.find((item) => item.key === key);
    if (!preset || !metadata) return;
    setPresetKey(key);
    setRole(preset.role);
    setMinimumAppearances(preset.minimumAppearances);
    setWeights(Object.fromEntries(metadata.metrics.map((metric) => [metric.key, preset.weights[metric.key] ?? 0])));
    setResult(null);
  };

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
            gruppo filtrato e resta ispezionabile. Parti da uno degli esempi e
            poi modifica liberamente i pesi.
          </p>
        </div>
      </header>

      <section className="ranking-config">
        <div className="preset-panel">
          <div><span className="eyebrow">Configurazioni di esempio</span><h2>Un punto di partenza per ogni ruolo</h2><p>{RANKING_PRESETS.find((item) => item.key === presetKey)?.description}</p></div>
          <label className="field"><span>Preset</span><select value={presetKey} onChange={(event) => loadPreset(event.target.value)}>{RANKING_PRESETS.map((preset) => <option key={preset.key} value={preset.key}>{preset.name} · {preset.role}</option>)}</select></label>
        </div>
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
                const rolePreset = RANKING_PRESETS.find((item) => item.role === nextRole);
                if (rolePreset) {
                  loadPreset(rolePreset.key);
                  return;
                }
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
          {seasons.filter((season) => !season.is_current).map((season) => (
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
                  <th>Trend recente</th>
                  <th>Affidabilità</th>
                  <th>Composizione</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => (
                  <tr key={item.player_id}>
                    <td>{item.position}</td>
                    <td><Link className="player-link" to={`/players/${item.player_id}`} state={{
                      from: "rankings",
                      rankingState: {
                        role,
                        selectedSeasons,
                        minimumAppearances,
                        decay,
                        continuityThreshold,
                        weights,
                        result,
                        presetKey
                      } satisfies RankingViewState
                    }}><strong>{item.display_name}</strong></Link></td>
                    <td><strong>{formatNumber(item.score, 1)}</strong></td>
                    <td>{item.total_pv ?? "—"}</td>
                    <td>
                      {item.fantasy_average_trend_slope === null ? "—" : (
                        <div className={`ranking-trend ${trendDirection(item.fantasy_average_trend_slope) === 1 ? "ranking-trend--up" : trendDirection(item.fantasy_average_trend_slope) === -1 ? "ranking-trend--down" : ""}`}>
                          <strong>
                            {trendDirection(item.fantasy_average_trend_slope) === 1 ? "↑" : trendDirection(item.fantasy_average_trend_slope) === -1 ? "↓" : "→"}{" "}
                            {item.metrics.fantasy_average_trend_slope
                              ? `${formatNumber(item.metrics.fantasy_average_trend_slope.percentile, 0)}° pct`
                              : "trend"}
                          </strong>
                          <small>
                            pendenza {trendDirection(item.fantasy_average_trend_slope) === 1 ? "+" : ""}{formatNumber(item.fantasy_average_trend_slope, 2)}
                            {item.fantasy_average_absolute_change === null ? "" : ` · ultima ${item.fantasy_average_absolute_change > 0 ? "+" : ""}${formatNumber(item.fantasy_average_absolute_change, 2)}`}
                          </small>
                          <small>{item.seasons_with_pv ?? 0} stagioni · {item.total_pv ?? 0} Pv</small>
                        </div>
                      )}
                    </td>
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
