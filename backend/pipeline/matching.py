"""Matching trasparente dei giocatori, senza fusioni fuzzy automatiche."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


MATCH_STATUSES = {
    "certain_external_id",
    "manual_confirmed",
    "new_player",
}
REVIEW_STATUSES = {"possible_match", "homonym", "conflict"}


@dataclass(frozen=True)
class ManualMapping:
    source_provider: str
    source_external_id: str
    target_provider: str
    target_external_id: str
    note: str | None = None


@dataclass
class PlayerIdentity:
    internal_key: str
    primary_provider: str
    primary_external_id: str
    display_name: str
    normalized_name: str
    match_key: str
    aliases: set[str] = field(default_factory=set)
    external_keys: set[tuple[str, str]] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)
    teams: set[str] = field(default_factory=set)
    seasons: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class MatchCandidate:
    internal_key: str
    display_name: str
    score: float
    roles: tuple[str, ...]
    teams: tuple[str, ...]
    seasons: tuple[str, ...]


@dataclass(frozen=True)
class MatchReview:
    review_type: str
    source_provider: str
    source_external_id: str
    source_name: str
    source_season: str
    reason: str
    candidates: tuple[MatchCandidate, ...]


@dataclass(frozen=True)
class MatchDecision:
    internal_key: str
    source_provider: str
    source_external_id: str
    source_name: str
    source_season: str
    status: str


@dataclass(frozen=True)
class MatchResult:
    identities: tuple[PlayerIdentity, ...]
    decisions: tuple[MatchDecision, ...]
    reviews: tuple[MatchReview, ...]


def load_manual_mappings(path: Path) -> tuple[ManualMapping, ...]:
    with path.open("r", encoding="utf-8") as stream:
        raw = json.load(stream)
    if raw.get("mapping_schema_version") != 1:
        raise ValueError("Versione mapping manuale non supportata")

    mappings = tuple(
        ManualMapping(
            source_provider=str(item["source_provider"]),
            source_external_id=str(item["source_external_id"]),
            target_provider=str(item["target_provider"]),
            target_external_id=str(item["target_external_id"]),
            note=item.get("note"),
        )
        for item in raw.get("mappings", ())
    )
    sources = [
        (mapping.source_provider, mapping.source_external_id)
        for mapping in mappings
    ]
    if len(sources) != len(set(sources)):
        raise ValueError("Un identificativo sorgente ha più mapping manuali")
    for mapping in mappings:
        if (
            mapping.source_provider,
            mapping.source_external_id,
        ) == (
            mapping.target_provider,
            mapping.target_external_id,
        ):
            raise ValueError("Un mapping manuale non può puntare a se stesso")
    return mappings


def _similarity(first: str, second: str) -> float:
    return round(SequenceMatcher(None, first, second).ratio() * 100, 2)


class PlayerMatcher:
    """Registro in-memory; solo ID e mapping manuali possono unire identità."""

    def __init__(
        self,
        manual_mappings: Sequence[ManualMapping] = (),
        *,
        fuzzy_threshold: float = 92.0,
        max_candidates: int = 3,
    ) -> None:
        self._identities: list[PlayerIdentity] = []
        self._by_external_key: dict[tuple[str, str], PlayerIdentity] = {}
        self._manual = {
            (mapping.source_provider, mapping.source_external_id): mapping
            for mapping in manual_mappings
        }
        self._fuzzy_threshold = fuzzy_threshold
        self._max_candidates = max_candidates
        self._decisions: list[MatchDecision] = []
        self._reviews: list[MatchReview] = []

    def _new_identity(
        self,
        provider: str,
        external_id: str,
        record: Mapping[str, Any],
    ) -> PlayerIdentity:
        identity = PlayerIdentity(
            internal_key=f"player-{len(self._identities) + 1:06d}",
            primary_provider=provider,
            primary_external_id=external_id,
            display_name=str(record["source_player_name"]),
            normalized_name=str(record["normalized_player_name"]),
            match_key=str(record["player_match_key"]),
        )
        identity.external_keys.add((provider, external_id))
        self._identities.append(identity)
        self._by_external_key[(provider, external_id)] = identity
        return identity

    def _candidate_matches(
        self,
        record: Mapping[str, Any],
        *,
        excluded: PlayerIdentity | None = None,
    ) -> tuple[MatchCandidate, ...]:
        candidates: list[MatchCandidate] = []
        match_key = str(record["player_match_key"])
        for identity in self._identities:
            if identity is excluded:
                continue
            score = _similarity(match_key, identity.match_key)
            if score < self._fuzzy_threshold:
                continue
            candidates.append(
                MatchCandidate(
                    internal_key=identity.internal_key,
                    display_name=identity.display_name,
                    score=score,
                    roles=tuple(sorted(identity.roles)),
                    teams=tuple(sorted(identity.teams)),
                    seasons=tuple(sorted(identity.seasons)),
                )
            )
        return tuple(
            sorted(
                candidates,
                key=lambda candidate: (-candidate.score, candidate.display_name),
            )[: self._max_candidates]
        )

    @staticmethod
    def _update_identity(
        identity: PlayerIdentity,
        record: Mapping[str, Any],
        season: str,
    ) -> None:
        identity.aliases.add(str(record["source_player_name"]))
        identity.roles.add(str(record["classic_role"]))
        identity.teams.add(str(record["source_team_name"]))
        identity.seasons.add(season)

    def add_record(
        self,
        record: Mapping[str, Any],
        *,
        season: str,
        provider: str,
    ) -> MatchDecision:
        external_id = str(record["external_player_id"])
        source_key = (provider, external_id)
        identity = self._by_external_key.get(source_key)
        status = "certain_external_id"

        if identity is None and source_key in self._manual:
            manual = self._manual[source_key]
            target_key = (manual.target_provider, manual.target_external_id)
            identity = self._by_external_key.get(target_key)
            if identity is None:
                identity = self._new_identity(
                    manual.target_provider,
                    manual.target_external_id,
                    record,
                )
            identity.external_keys.add(source_key)
            self._by_external_key[source_key] = identity
            status = "manual_confirmed"

        if identity is None:
            candidates = self._candidate_matches(record)
            identity = self._new_identity(provider, external_id, record)
            status = "new_player"
            if candidates:
                review_type = (
                    "homonym"
                    if any(candidate.score == 100 for candidate in candidates)
                    else "possible_match"
                )
                self._reviews.append(
                    MatchReview(
                        review_type=review_type,
                        source_provider=provider,
                        source_external_id=external_id,
                        source_name=str(record["source_player_name"]),
                        source_season=season,
                        reason=(
                            "Nome normalizzato identico con ID esterno differente"
                            if review_type == "homonym"
                            else "Similarità del nome sopra la soglia; nessuna fusione eseguita"
                        ),
                        candidates=candidates,
                    )
                )

        self._update_identity(identity, record, season)
        decision = MatchDecision(
            internal_key=identity.internal_key,
            source_provider=provider,
            source_external_id=external_id,
            source_name=str(record["source_player_name"]),
            source_season=season,
            status=status,
        )
        if status not in MATCH_STATUSES:
            raise AssertionError(f"Stato decisione non previsto: {status}")
        self._decisions.append(decision)
        return decision

    def result(self) -> MatchResult:
        return MatchResult(
            identities=tuple(self._identities),
            decisions=tuple(self._decisions),
            reviews=tuple(self._reviews),
        )


def match_records(
    records: Iterable[tuple[str, Mapping[str, Any]]],
    *,
    provider: str,
    manual_mappings: Sequence[ManualMapping] = (),
    fuzzy_threshold: float = 92.0,
) -> MatchResult:
    matcher = PlayerMatcher(
        manual_mappings,
        fuzzy_threshold=fuzzy_threshold,
    )
    for season, record in records:
        matcher.add_record(record, season=season, provider=provider)
    return matcher.result()

