"""Normalizzazione pura dei valori sorgente, senza scritture su database."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from backend.pipeline.column_mapping import ColumnMapping, canonicalize_record


NULL_TOKENS = frozenset({"", "-", "n.d.", "nd", "n/a", "na", "null", "none"})
CLASSIC_ROLES = frozenset({"P", "D", "C", "A"})
MANTRA_ROLES = frozenset(
    {"Por", "B", "Dd", "Ds", "Dc", "E", "M", "C", "W", "T", "A", "Pc"}
)
APOSTROPHE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u02bc": "'",
        "\u0060": "'",
        "\u00b4": "'",
    }
)


class NormalizationError(ValueError):
    """Errore esplicito di conversione o dominio."""


@dataclass(frozen=True)
class NormalizedName:
    display: str
    normalized: str
    match_key: str


@dataclass(frozen=True)
class NormalizedRecord:
    raw: dict[str, Any]
    canonical_source: dict[str, Any]
    analytical: dict[str, Any]


def normalize_text(value: Any) -> str:
    """Applica NFC, apostrofi uniformi e spazi singoli."""

    if value is None:
        raise NormalizationError("Il testo obbligatorio non può essere null")
    text = unicodedata.normalize("NFC", str(value))
    text = text.translate(APOSTROPHE_TRANSLATION)
    text = " ".join(text.strip().split())
    if not text:
        raise NormalizationError("Il testo obbligatorio non può essere vuoto")
    return text


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def normalize_name(value: Any) -> NormalizedName:
    """Produce display pulito, forma casefold e chiave permissiva di confronto."""

    display = normalize_text(value)
    normalized = display.casefold()
    match_key = _strip_accents(normalized)
    match_key = re.sub(r"[^a-z0-9]+", " ", match_key)
    match_key = " ".join(match_key.split())
    return NormalizedName(
        display=display,
        normalized=normalized,
        match_key=match_key,
    )


def normalize_team(value: Any) -> tuple[str, str]:
    """Normalizza meccanicamente la squadra senza alias inventati."""

    display = normalize_text(value)
    return display, _strip_accents(display.casefold())


def normalize_classic_role(value: Any) -> str:
    role = normalize_text(value).upper()
    if role not in CLASSIC_ROLES:
        raise NormalizationError(f"Ruolo Classic non riconosciuto: {value!r}")
    return role


def normalize_mantra_roles(value: Any) -> tuple[str, ...]:
    """Conserva l'ordine sorgente, rimuovendo soltanto duplicati."""

    raw_tokens = [normalize_text(token) for token in normalize_text(value).split(";")]
    roles: list[str] = []
    for token in raw_tokens:
        if token not in MANTRA_ROLES:
            raise NormalizationError(f"Ruolo Mantra non riconosciuto: {token!r}")
        if token not in roles:
            roles.append(token)
    return tuple(roles)


def parse_decimal(value: Any, *, allow_percentage: bool = False) -> Decimal | None:
    """Converte numeri Python o stringhe italiane senza usare float intermedi."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise NormalizationError("Un booleano non è un valore numerico valido")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    if isinstance(value, str) and not value.strip():
        return None
    text = normalize_text(value)
    if text.casefold() in NULL_TOKENS:
        return None

    percentage = text.endswith("%")
    if percentage and not allow_percentage:
        raise NormalizationError(f"Percentuale non ammessa: {value!r}")
    if percentage:
        text = text[:-1].strip()

    text = text.replace(" ", "")
    if "," in text:
        # Formato italiano: il punto è separatore delle migliaia.
        text = text.replace(".", "").replace(",", ".")

    try:
        parsed = Decimal(text)
    except InvalidOperation as error:
        raise NormalizationError(f"Numero non convertibile: {value!r}") from error
    return parsed / Decimal(100) if percentage else parsed


def parse_integer(value: Any) -> int | None:
    parsed = parse_decimal(value)
    if parsed is None:
        return None
    integral = parsed.to_integral_value()
    if parsed != integral:
        raise NormalizationError(f"Intero atteso, ricevuto: {value!r}")
    return int(integral)


def _required_integer(value: Any, field: str) -> int:
    parsed = parse_integer(value)
    if parsed is None:
        raise NormalizationError(f"{field}: valore intero obbligatorio")
    return parsed


def _required_decimal(value: Any, field: str) -> Decimal:
    parsed = parse_decimal(value)
    if parsed is None:
        raise NormalizationError(f"{field}: valore numerico obbligatorio")
    return parsed


def normalize_source_record(
    source_record: Mapping[str, Any],
    mapping: ColumnMapping,
) -> NormalizedRecord:
    """Normalizza una riga, mantenendo separati raw, canonico e analitico."""

    raw = dict(source_record)
    canonical = canonicalize_record(raw, mapping)
    name = normalize_name(canonical["source_player_name"])
    team_display, team_normalized = normalize_team(canonical["source_team_name"])
    rated_appearances = _required_integer(
        canonical["rated_appearances"], "rated_appearances"
    )
    if rated_appearances < 0:
        raise NormalizationError("rated_appearances non può essere negativo")

    analytical: dict[str, Any] = {
        "external_player_id": str(
            _required_integer(canonical["external_player_id"], "external_player_id")
        ),
        "source_player_name": name.display,
        "normalized_player_name": name.normalized,
        "player_match_key": name.match_key,
        "source_team_name": team_display,
        "normalized_team_name": team_normalized,
        "classic_role": normalize_classic_role(canonical["classic_role"]),
        "mantra_roles": normalize_mantra_roles(canonical["mantra_roles"]),
        "rated_appearances": rated_appearances,
    }

    for field in ("average_rating", "fantasy_average"):
        source_value = _required_decimal(canonical[field], field)
        analytical[field] = None if rated_appearances == 0 else source_value

    additive_fields = (
        "goals_scored",
        "goals_conceded",
        "penalties_saved",
        "penalties_taken",
        "penalties_scored",
        "penalties_missed",
        "assists",
        "yellow_cards",
        "red_cards",
        "own_goals",
    )
    for field in additive_fields:
        value = _required_integer(canonical[field], field)
        if value < 0:
            raise NormalizationError(f"{field} non può essere negativo")
        analytical[field] = value

    analytical["has_valid_rating"] = rated_appearances > 0
    return NormalizedRecord(
        raw=raw,
        canonical_source=canonical,
        analytical=analytical,
    )
