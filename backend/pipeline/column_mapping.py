"""Caricamento e validazione del mapping fra colonne sorgente e canoniche."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ALLOWED_DATA_TYPES = {"integer", "number", "string"}
ALLOWED_AGGREGATIONS = {
    "not_applicable",
    "sum_if_disjoint",
    "weighted_mean",
}
ALLOWED_ZERO_POLICIES = {
    "valid",
    "not_applicable",
    "null_when_pv_zero",
}


@dataclass(frozen=True)
class ColumnDefinition:
    source: str
    canonical: str
    data_type: str
    nullable: bool
    category: str
    aggregation: str
    zero_policy: str
    semantic_status: str
    description: str
    weight_column: str | None = None


@dataclass(frozen=True)
class ColumnMapping:
    schema_version: int
    provider: str
    applies_to: tuple[str, ...]
    columns: tuple[ColumnDefinition, ...]

    @property
    def source_columns(self) -> tuple[str, ...]:
        return tuple(column.source for column in self.columns)

    @property
    def canonical_columns(self) -> tuple[str, ...]:
        return tuple(column.canonical for column in self.columns)

    def by_source(self) -> dict[str, ColumnDefinition]:
        return {column.source: column for column in self.columns}


@dataclass(frozen=True)
class HeaderValidation:
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]
    duplicate: tuple[str, ...]
    order_matches: bool

    @property
    def is_valid(self) -> bool:
        return not self.missing and not self.unexpected and not self.duplicate


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _require_string(raw: Mapping[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Il campo {field!r} deve essere una stringa non vuota")
    return value


def _parse_column(raw: Mapping[str, Any]) -> ColumnDefinition:
    data_type = _require_string(raw, "data_type")
    aggregation = _require_string(raw, "aggregation")
    zero_policy = _require_string(raw, "zero_policy")
    if data_type not in ALLOWED_DATA_TYPES:
        raise ValueError(f"Tipo non supportato: {data_type}")
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"Aggregazione non supportata: {aggregation}")
    if zero_policy not in ALLOWED_ZERO_POLICIES:
        raise ValueError(f"Politica zero non supportata: {zero_policy}")
    if not isinstance(raw.get("nullable"), bool):
        raise ValueError("Il campo 'nullable' deve essere booleano")

    weight_column = raw.get("weight_column")
    if weight_column is not None and not isinstance(weight_column, str):
        raise ValueError("'weight_column' deve essere una stringa o null")
    if aggregation == "weighted_mean" and not weight_column:
        raise ValueError("Una media ponderata richiede 'weight_column'")

    return ColumnDefinition(
        source=_require_string(raw, "source"),
        canonical=_require_string(raw, "canonical"),
        data_type=data_type,
        nullable=raw["nullable"],
        category=_require_string(raw, "category"),
        aggregation=aggregation,
        zero_policy=zero_policy,
        semantic_status=_require_string(raw, "semantic_status"),
        description=_require_string(raw, "description"),
        weight_column=weight_column,
    )


def load_column_mapping(path: Path) -> ColumnMapping:
    """Carica un mapping YAML espresso nel sottoinsieme JSON."""

    with path.open("r", encoding="utf-8") as stream:
        raw = json.load(stream)

    columns = tuple(_parse_column(column) for column in raw.get("columns", ()))
    if not columns:
        raise ValueError("Il mapping deve contenere almeno una colonna")

    duplicate_sources = _duplicates(column.source for column in columns)
    duplicate_canonical = _duplicates(column.canonical for column in columns)
    if duplicate_sources:
        raise ValueError(f"Colonne sorgente duplicate: {duplicate_sources}")
    if duplicate_canonical:
        raise ValueError(f"Colonne canoniche duplicate: {duplicate_canonical}")

    source_columns = {column.source for column in columns}
    missing_weights = sorted(
        {
            column.weight_column
            for column in columns
            if column.weight_column and column.weight_column not in source_columns
        }
    )
    if missing_weights:
        raise ValueError(f"Colonne peso non definite: {missing_weights}")

    schema_version = raw.get("mapping_schema_version")
    if not isinstance(schema_version, int) or schema_version < 1:
        raise ValueError("'mapping_schema_version' deve essere un intero positivo")

    applies_to = tuple(raw.get("applies_to", ()))
    if not applies_to or not all(isinstance(value, str) for value in applies_to):
        raise ValueError("'applies_to' deve contenere almeno una stagione")
    if _duplicates(applies_to):
        raise ValueError("Le stagioni in 'applies_to' devono essere univoche")

    return ColumnMapping(
        schema_version=schema_version,
        provider=_require_string(raw, "provider"),
        applies_to=applies_to,
        columns=columns,
    )


def validate_headers(
    actual_headers: Sequence[str],
    mapping: ColumnMapping,
) -> HeaderValidation:
    """Confronta intestazioni reali e mapping senza ignorare differenze."""

    expected = mapping.source_columns
    duplicate = _duplicates(actual_headers)
    return HeaderValidation(
        missing=tuple(sorted(set(expected) - set(actual_headers))),
        unexpected=tuple(sorted(set(actual_headers) - set(expected))),
        duplicate=duplicate,
        order_matches=tuple(actual_headers) == expected,
    )


def canonicalize_record(
    source_record: Mapping[str, Any],
    mapping: ColumnMapping,
) -> dict[str, Any]:
    """Rinomina le chiavi senza applicare ancora conversioni o normalizzazioni."""

    validation = validate_headers(tuple(source_record.keys()), mapping)
    if not validation.is_valid:
        raise ValueError(
            "Record incompatibile con il mapping: "
            f"missing={validation.missing}, unexpected={validation.unexpected}, "
            f"duplicate={validation.duplicate}"
        )
    return {
        definition.canonical: source_record[definition.source]
        for definition in mapping.columns
    }

