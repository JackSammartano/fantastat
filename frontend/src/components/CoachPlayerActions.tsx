import { useCoach } from "../coach/CoachContext";
import type { CoachPlayer } from "../coach/types";

export function CoachPlayerActions({ player, compact = false }: { player: CoachPlayer; compact?: boolean }) {
  const coach = useCoach();
  return <div className={`coach-actions${compact ? " coach-actions--compact" : ""}`}>
    <button className={`coach-action${coach.isFavorite(player.id) ? " coach-action--active" : ""}`} type="button" onClick={() => coach.toggleFavorite(player)} aria-label={coach.isFavorite(player.id) ? `Rimuovi ${player.name} dai preferiti` : `Aggiungi ${player.name} ai preferiti`}>
      {coach.isFavorite(player.id) ? "★" : "☆"}<span>{compact ? "" : "Preferito"}</span>
    </button>
    <button className={`coach-action${coach.isInSquad(player.id) ? " coach-action--squad" : ""}`} type="button" onClick={() => coach.isInSquad(player.id) ? coach.removeFromSquad(player.id) : coach.addToSquad(player)} aria-label={coach.isInSquad(player.id) ? `Rimuovi ${player.name} dalla rosa` : `Aggiungi ${player.name} alla rosa`}>
      {coach.isInSquad(player.id) ? "✓" : "+"}<span>{compact ? "" : "La mia rosa"}</span>
    </button>
  </div>;
}
