"""Validazione esplicita di record normalizzati e dataset stagionali."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ADDITIVE_FIELDS = (
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


@dataclass(frozen=True)
class ValidationRules:
    schema_version: int
    max_rated_appearances: int
    average_rating_min: Decimal
    average_rating_max: Decimal
    warn_additive_with_zero_appearances: bool
    warn_goals_greater_than_appearances: bool
    warn_assists_greater_than_appearances: bool


@dataclass(frozen=True)
class RecordContext:
    season: str
    source_file: str
    sheet_name: str
    source_row_number: int
    record: Mapping[str, Any]


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    season: str
    source_file: str
    sheet_name: str
    source_row_number: int
    external_player_id: str | None
    player_name: str | None
    field: str | None = None
    actual_value: Any = None


@dataclass(frozen=True)
class ValidationResult:
    input_rows: int
    valid_rows: int
    excluded_rows: int
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")


def load_validation_rules(path: Path) -> ValidationRules:
    with path.open("r", encoding="utf-8") as stream:
        raw = json.load(stream)
    if raw.get("validation_schema_version") != 1:
        raise ValueError("Versione delle regole di validazione non supportata")
    maximum = int(raw["max_rated_appearances"])
    minimum_rating = Decimal(str(raw["average_rating_min"]))
    maximum_rating = Decimal(str(raw["average_rating_max"]))
    if maximum <= 0:
        raise ValueError("max_rated_appearances deve essere positivo")
    if minimum_rating >= maximum_rating:
        raise ValueError("Intervallo average_rating non valido")
    return ValidationRules(
        schema_version=1,
        max_rated_appearances=maximum,
        average_rating_min=minimum_rating,
        average_rating_max=maximum_rating,
        warn_additive_with_zero_appearances=bool(
            raw["warn_additive_with_zero_appearances"]
        ),
        warn_goals_greater_than_appearances=bool(
            raw["warn_goals_greater_than_appearances"]
        ),
        warn_assists_greater_than_appearances=bool(
            raw["warn_assists_greater_than_appearances"]
        ),
    )


def _issue(
    context: RecordContext,
    *,
    severity: str,
    code: str,
    message: str,
    field: str | None = None,
    actual_value: Any = None,
) -> ValidationIssue:
    record = context.record
    return ValidationIssue(
        severity=severity,
        code=code,
        message=message,
        season=context.season,
        source_file=context.source_file,
        sheet_name=context.sheet_name,
        source_row_number=context.source_row_number,
        external_player_id=(
            str(record["external_player_id"])
            if record.get("external_player_id") is not None
            else None
        ),
        player_name=(
            str(record["source_player_name"])
            if record.get("source_player_name") is not None
            else None
        ),
        field=field,
        actual_value=actual_value,
    )


def validate_record(
    context: RecordContext,
    rules: ValidationRules,
) -> tuple[ValidationIssue, ...]:
    record = context.record
    issues: list[ValidationIssue] = []
    pv = int(record["rated_appearances"])

    if pv < 0 or pv > rules.max_rated_appearances:
        issues.append(
            _issue(
                context,
                severity="error",
                code="VAL-RANGE-PV",
                message=(
                    "Le partite a voto devono essere comprese tra 0 e "
                    f"{rules.max_rated_appearances}"
                ),
                field="rated_appearances",
                actual_value=pv,
            )
        )

    average_rating = record.get("average_rating")
    fantasy_average = record.get("fantasy_average")
    if pv == 0 and (average_rating is not None or fantasy_average is not None):
        issues.append(
            _issue(
                context,
                severity="error",
                code="VAL-RATING-WITHOUT-PV",
                message="Con zero partite a voto le medie analitiche devono essere null",
                field="average_rating,fantasy_average",
                actual_value=[average_rating, fantasy_average],
            )
        )
    if pv > 0 and (average_rating is None or fantasy_average is None):
        issues.append(
            _issue(
                context,
                severity="error",
                code="VAL-RATING-MISSING",
                message="Con partite a voto positive entrambe le medie sono obbligatorie",
                field="average_rating,fantasy_average",
                actual_value=[average_rating, fantasy_average],
            )
        )
    if average_rating is not None and not (
        rules.average_rating_min
        <= Decimal(str(average_rating))
        <= rules.average_rating_max
    ):
        issues.append(
            _issue(
                context,
                severity="error",
                code="VAL-RANGE-MV",
                message="La media voto deve essere compresa nell'intervallo configurato",
                field="average_rating",
                actual_value=average_rating,
            )
        )

    for field in ADDITIVE_FIELDS:
        value = int(record[field])
        if value < 0:
            issues.append(
                _issue(
                    context,
                    severity="error",
                    code="VAL-NEGATIVE",
                    message="Una statistica additiva non può essere negativa",
                    field=field,
                    actual_value=value,
                )
            )

    penalties_taken = int(record["penalties_taken"])
    penalty_components = int(record["penalties_scored"]) + int(
        record["penalties_missed"]
    )
    if penalties_taken != penalty_components:
        issues.append(
            _issue(
                context,
                severity="error",
                code="VAL-PENALTY-IDENTITY",
                message="penalties_taken deve uguagliare scored + missed",
                field="penalties_taken",
                actual_value={
                    "taken": penalties_taken,
                    "scored_plus_missed": penalty_components,
                },
            )
        )

    non_zero_additive = [
        field for field in ADDITIVE_FIELDS if int(record[field]) != 0
    ]
    if (
        rules.warn_additive_with_zero_appearances
        and pv == 0
        and non_zero_additive
    ):
        issues.append(
            _issue(
                context,
                severity="warning",
                code="VAL-ADDITIVE-WITHOUT-PV",
                message=(
                    "Statistiche additive presenti con zero partite a voto; "
                    "la riga viene conservata"
                ),
                field=",".join(non_zero_additive),
                actual_value={
                    field: record[field] for field in non_zero_additive
                },
            )
        )

    if (
        rules.warn_goals_greater_than_appearances
        and pv > 0
        and int(record["goals_scored"]) > pv
    ):
        issues.append(
            _issue(
                context,
                severity="warning",
                code="VAL-GOALS-GT-PV",
                message="Gol segnati superiori alle partite a voto",
                field="goals_scored",
                actual_value=record["goals_scored"],
            )
        )
    if (
        rules.warn_assists_greater_than_appearances
        and pv > 0
        and int(record["assists"]) > pv
    ):
        issues.append(
            _issue(
                context,
                severity="warning",
                code="VAL-ASSISTS-GT-PV",
                message="Assist superiori alle partite a voto",
                field="assists",
                actual_value=record["assists"],
            )
        )
    return tuple(issues)


def validate_dataset(
    contexts: Sequence[RecordContext],
    rules: ValidationRules,
    *,
    excluded_rows: int = 0,
) -> ValidationResult:
    issues: list[ValidationIssue] = []
    for context in contexts:
        issues.extend(validate_record(context, rules))

    keys = [
        (context.season, str(context.record.get("external_player_id")))
        for context in contexts
    ]
    duplicate_keys = {
        key for key, count in Counter(keys).items() if count > 1
    }
    for context in contexts:
        key = (context.season, str(context.record.get("external_player_id")))
        if key in duplicate_keys:
            issues.append(
                _issue(
                    context,
                    severity="error",
                    code="VAL-DUPLICATE-PLAYER-SEASON",
                    message="ID esterno duplicato nella stessa stagione",
                    field="external_player_id",
                    actual_value=key[1],
                )
            )

    issues.sort(
        key=lambda issue: (
            issue.severity,
            issue.season,
            issue.source_file,
            issue.source_row_number,
            issue.code,
        )
    )
    return ValidationResult(
        input_rows=len(contexts) + excluded_rows,
        valid_rows=len(contexts),
        excluded_rows=excluded_rows,
        issues=tuple(issues),
    )


def issue_counts(issues: Iterable[ValidationIssue]) -> dict[str, int]:
    counts = Counter(issue.code for issue in issues)
    return {code: counts[code] for code in sorted(counts)}

