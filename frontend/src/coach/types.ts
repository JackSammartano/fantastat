import type { Role } from "../models/api";

export type WatchPriority = "high" | "alternative" | "bet";

export interface CoachPlayer {
  id: number;
  externalPlayerId: string | null;
  name: string;
  role: Role;
  team: string;
  quotation: number | null;
  fvm: number | null;
}

export interface FavoritePlayer {
  player: CoachPlayer;
  priority: WatchPriority;
  maxBid: number | null;
  note: string;
  addedAt: string;
}

export interface SquadPlayer {
  player: CoachPlayer;
  purchasePrice: number;
  note: string;
  addedAt: string;
}

export interface CoachSettings {
  initialBudget: number;
  roleLimits: Record<Role, number>;
}

export interface CoachState {
  version: 1;
  favorites: FavoritePlayer[];
  squad: SquadPlayer[];
  settings: CoachSettings;
}

export interface MatchdayPlayerVote {
  externalPlayerId: string;
  role: Role;
  name: string;
  team: string;
  vote: number | null;
  goalsScored: number;
  goalsConceded: number;
  penaltiesSaved: number;
  penaltiesScored: number;
  penaltiesMissed: number;
  ownGoals: number;
  yellowCards: number;
  redCards: number;
  assists: number;
}

export interface MatchdayImport {
  key: string;
  season: string;
  matchday: number;
  source: string;
  fileName: string;
  fileHash: string;
  importedAt: string;
  ignoredNonPlayers: number;
  votes: MatchdayPlayerVote[];
}
