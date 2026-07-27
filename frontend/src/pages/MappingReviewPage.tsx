import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { StatePanel } from "../components/StatePanel";
import type {
  MappingResolution,
  MergeAudit,
  MergePreview,
  PendingMapping
} from "../models/api";
import { formatNumber } from "../utils/format";

type Resolution = MappingResolution["resolution"];

const ACTIONS: Array<{
  resolution: Resolution;
  label: string;
  description: string;
  className: string;
}> = [
  {
    resolution: "confirm_candidate",
    label: "Analizza fusione",
    description: "Genera un'anteprima senza modificare i dati.",
    className: "button--primary"
  },
  {
    resolution: "new_player",
    label: "Mantieni separati",
    description: "Conferma che l'identità sorgente è distinta.",
    className: "button--secondary"
  },
  {
    resolution: "exclude",
    label: "Scarta suggerimento",
    description: "Chiude la revisione senza eliminare il record storico.",
    className: "button--danger"
  }
];

export function MappingReviewPage() {
  const [items, setItems] = useState<PendingMapping[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previews, setPreviews] = useState<Record<number, MergePreview>>({});
  const [confirmations, setConfirmations] = useState<Record<number, string>>({});
  const [lastMerge, setLastMerge] = useState<MergeAudit | null>(null);

  useEffect(() => {
    api
      .pendingMappings()
      .then(setItems)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Errore API")
      )
      .finally(() => setLoading(false));
  }, []);

  const resolve = async (item: PendingMapping, resolution: Resolution) => {
    if (resolution === "confirm_candidate") {
      setLoading(true);
      setError(null);
      try {
        const preview = await api.mergePreview(item.id);
        setPreviews((current) => ({ ...current, [item.id]: preview }));
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Errore API");
      } finally {
        setLoading(false);
      }
      return;
    }
    const action = ACTIONS.find((candidate) => candidate.resolution === resolution);
    if (
      !window.confirm(
        `${action?.label ?? "Conferma"} per ${item.source_name}? Questa decisione sarà registrata nel database locale.`
      )
    ) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.resolveMapping(item.id, {
        resolution,
        notes: notes[item.id]?.trim() || undefined
      });
      setItems((current) => current.filter((candidate) => candidate.id !== item.id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Errore API");
    } finally {
      setLoading(false);
    }
  };

  if (loading && items.length === 0) {
    return <StatePanel title="Caricamento" message="Lettura revisioni pendenti…" />;
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Controllo identità</span>
          <h1>Revisioni corrispondenze</h1>
          <p>
            I suggerimenti fuzzy non producono fusioni automatiche. Ogni azione
            richiede conferma e viene tracciata localmente.
          </p>
        </div>
        <strong>{items.length} pendenti</strong>
      </header>

      <aside className="mapping-warning">
        <strong>Operazione sensibile:</strong> la conferma del candidato apre
        prima un’anteprima. La fusione viene bloccata in presenza di conflitti,
        crea un backup locale e può essere applicata soltanto digitando
        esplicitamente <code>FONDI</code>.
      </aside>

      {error && <StatePanel title="Operazione non riuscita" message={error} tone="error" />}
      {lastMerge && (
        <aside className="merge-success">
          <div>
            <strong>Fusione applicata con audit #{lastMerge.id}</strong>
            <span>
              Backup: {lastMerge.backup_path ?? "gestito dal database di test"}
            </span>
          </div>
          <button
            className="button button--secondary"
            type="button"
            onClick={async () => {
              if (!window.confirm("Annullare l’ultima fusione applicata?")) return;
              try {
                await api.revertMerge(lastMerge.id);
                setLastMerge(null);
                setItems(await api.pendingMappings());
              } catch (reason) {
                setError(reason instanceof Error ? reason.message : "Errore API");
              }
            }}
          >
            Annulla fusione
          </button>
        </aside>
      )}
      {!error && items.length === 0 ? (
        <StatePanel title="Nessuna revisione pendente" message="Tutte le decisioni risultano registrate." />
      ) : (
        <div className="mapping-list">
          {items.map((item) => (
            <article className="mapping-card" key={item.id}>
              <div className="mapping-card__heading">
                <div>
                  <span className="eyebrow">{item.season}</span>
                  <h2>{item.source_name}</h2>
                  <small>ID sorgente {item.source_external_player_id}</small>
                </div>
                <div className="similarity-score">
                  <strong>{formatNumber(item.candidate.similarity_score, 1)}%</strong>
                  <span>similarità</span>
                </div>
              </div>

              <div className="identity-comparison">
                <section>
                  <span>Sorgente</span>
                  <h3>{item.source_name}</h3>
                  <p>
                    {item.source_role ?? "?"} · {item.source_team ?? "—"} ·{" "}
                    {item.source_rated_appearances ?? "—"} Pv
                  </p>
                  {item.source_player_id && (
                    <Link to={`/players/${item.source_player_id}`}>Apri storico sorgente</Link>
                  )}
                </section>
                <span className="identity-comparison__arrow">→</span>
                <section>
                  <span>Candidato suggerito</span>
                  <h3>{item.candidate.display_name ?? "Nessun candidato"}</h3>
                  <p>
                    {item.candidate.roles.join(", ") || "?"} ·{" "}
                    {item.candidate.teams.join(", ") || "—"}
                  </p>
                  <small>{item.candidate.seasons.join(" · ")}</small>
                  {item.candidate.player_id && (
                    <Link to={`/players/${item.candidate.player_id}`}>Apri storico candidato</Link>
                  )}
                </section>
              </div>

              <p className="mapping-reason">{item.reason}</p>
              {previews[item.id] && (
                <section
                  className={`merge-preview${
                    previews[item.id].blocked ? " merge-preview--blocked" : ""
                  }`}
                >
                  <h3>Anteprima fusione</h3>
                  <p>
                    {previews[item.id].source_name} →{" "}
                    {previews[item.id].target_name}
                  </p>
                  <dl>
                    <div>
                      <dt>Stagioni da spostare</dt>
                      <dd>
                        {previews[item.id].seasons_to_move.join(", ") || "nessuna"}
                      </dd>
                    </div>
                    <div>
                      <dt>Sovrapposizioni</dt>
                      <dd>
                        {previews[item.id].overlapping_seasons.join(", ") ||
                          "nessuna"}
                      </dd>
                    </div>
                    <div>
                      <dt>Conflitti alias</dt>
                      <dd>
                        {previews[item.id].alias_conflicts.join(", ") || "nessuno"}
                      </dd>
                    </div>
                  </dl>
                  {previews[item.id].blocked ? (
                    <strong>
                      Fusione bloccata: {previews[item.id].blockers.join("; ")}
                    </strong>
                  ) : (
                    <div className="merge-confirm">
                      <label className="field">
                        <span>Digita FONDI per applicare</span>
                        <input
                          value={confirmations[item.id] ?? ""}
                          onChange={(event) =>
                            setConfirmations((current) => ({
                              ...current,
                              [item.id]: event.target.value
                            }))
                          }
                        />
                      </label>
                      <button
                        className="button button--danger"
                        type="button"
                        disabled={confirmations[item.id] !== "FONDI" || loading}
                        onClick={async () => {
                          if (
                            !window.confirm(
                              `Ultima conferma: fondere ${item.source_name} in ${item.candidate.display_name}?`
                            )
                          ) {
                            return;
                          }
                          setLoading(true);
                          try {
                            const audit = await api.applyMerge(
                              item.id,
                              previews[item.id].preview_token,
                              notes[item.id]?.trim() || undefined
                            );
                            setLastMerge(audit);
                            setItems((current) =>
                              current.filter((candidate) => candidate.id !== item.id)
                            );
                          } catch (reason) {
                            setError(
                              reason instanceof Error
                                ? reason.message
                                : "Errore API"
                            );
                          } finally {
                            setLoading(false);
                          }
                        }}
                      >
                        Applica fusione con backup
                      </button>
                    </div>
                  )}
                </section>
              )}
              <label className="field">
                <span>Nota della decisione</span>
                <textarea
                  value={notes[item.id] ?? ""}
                  maxLength={2000}
                  onChange={(event) =>
                    setNotes((current) => ({
                      ...current,
                      [item.id]: event.target.value
                    }))
                  }
                  placeholder="Motivazione facoltativa ma consigliata"
                />
              </label>
              <div className="mapping-actions">
                {ACTIONS.map((action) => (
                  <button
                    className={`button ${action.className}`}
                    type="button"
                    key={action.resolution}
                    title={action.description}
                    disabled={
                      loading ||
                      (action.resolution === "confirm_candidate" &&
                        item.candidate.player_id === null)
                    }
                    onClick={() => void resolve(item, action.resolution)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
