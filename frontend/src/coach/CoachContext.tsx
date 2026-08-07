import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { CoachPlayer, CoachSettings, CoachState, FavoritePlayer, SquadPlayer, WatchPriority } from "./types";
import type { CurrentListItem } from "../models/api";

const STORAGE_KEY = "fantalab-coach-state-v1";
const DEFAULT_SETTINGS: CoachSettings = { initialBudget: 500, roleLimits: { P: 3, D: 8, C: 8, A: 6 } };
const DEFAULT_STATE: CoachState = { version: 1, favorites: [], squad: [], settings: DEFAULT_SETTINGS };

interface CoachContextValue extends CoachState {
  isFavorite: (playerId: number) => boolean;
  isInSquad: (playerId: number) => boolean;
  toggleFavorite: (player: CoachPlayer) => void;
  updateFavorite: (playerId: number, patch: Partial<Pick<FavoritePlayer, "priority" | "maxBid" | "note">>) => void;
  addToSquad: (player: CoachPlayer, purchasePrice?: number) => void;
  updateSquadPlayer: (playerId: number, patch: Partial<Pick<SquadPlayer, "purchasePrice" | "note">>) => void;
  removeFromSquad: (playerId: number) => void;
  updateSettings: (settings: CoachSettings) => void;
  reconcileCurrentPlayers: (items: CurrentListItem[]) => void;
  exportBackup: () => string;
  importBackup: (value: string) => void;
}

const CoachContext = createContext<CoachContextValue | null>(null);

function loadState(): CoachState {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as CoachState | null;
    return parsed?.version === 1 ? parsed : DEFAULT_STATE;
  } catch {
    return DEFAULT_STATE;
  }
}

export function CoachProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CoachState>(loadState);
  const save = (next: CoachState) => { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); setState(next); };

  const value = useMemo<CoachContextValue>(() => ({
    ...state,
    isFavorite: (id) => state.favorites.some((item) => item.player.id === id),
    isInSquad: (id) => state.squad.some((item) => item.player.id === id),
    toggleFavorite: (player) => save({ ...state, favorites: state.favorites.some((item) => item.player.id === player.id)
      ? state.favorites.filter((item) => item.player.id !== player.id)
      : [...state.favorites, { player, priority: "alternative" as WatchPriority, maxBid: null, note: "", addedAt: new Date().toISOString() }] }),
    updateFavorite: (id, patch) => save({ ...state, favorites: state.favorites.map((item) => item.player.id === id ? { ...item, ...patch } : item) }),
    addToSquad: (player, purchasePrice = 0) => save({ ...state, favorites: state.favorites.filter((item) => item.player.id !== player.id), squad: state.squad.some((item) => item.player.id === player.id) ? state.squad : [...state.squad, { player, purchasePrice, note: "", addedAt: new Date().toISOString() }] }),
    updateSquadPlayer: (id, patch) => save({ ...state, squad: state.squad.map((item) => item.player.id === id ? { ...item, ...patch } : item) }),
    removeFromSquad: (id) => save({ ...state, squad: state.squad.filter((item) => item.player.id !== id) }),
    updateSettings: (settings) => save({ ...state, settings }),
    reconcileCurrentPlayers: (items) => {
      const current = new Map(items.filter((item) => item.external_player_id).map((item) => [item.external_player_id!, item]));
      const refreshPlayer = (player: CoachPlayer): CoachPlayer => {
        const updated = player.externalPlayerId ? current.get(player.externalPlayerId) : undefined;
        return updated ? { ...player, id: updated.player_id, name: updated.name, role: updated.classic_role, team: updated.team, quotation: updated.quotation, fvm: updated.fvm } : player;
      };
      save({ ...state, favorites: state.favorites.map((item) => ({ ...item, player: refreshPlayer(item.player) })), squad: state.squad.map((item) => ({ ...item, player: refreshPlayer(item.player) })) });
    },
    exportBackup: () => JSON.stringify(state, null, 2),
    importBackup: (raw) => { const parsed = JSON.parse(raw) as CoachState; if (parsed.version !== 1 || !Array.isArray(parsed.favorites) || !Array.isArray(parsed.squad)) throw new Error("Backup Fanta-Allenatore non valido"); save(parsed); }
  }), [state]);

  return <CoachContext.Provider value={value}>{children}</CoachContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCoach() {
  const value = useContext(CoachContext);
  if (!value) throw new Error("useCoach deve essere usato dentro CoachProvider");
  return value;
}
