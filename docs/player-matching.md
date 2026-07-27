# Matching dei giocatori

## Regola fondamentale

Nome, squadra e ruolo non sono chiavi definitive. Soltanto:

1. lo stesso identificativo esterno dello stesso provider;
2. una decisione manuale esplicita;

possono collegare automaticamente due record alla stessa identità.

## Stati delle decisioni

| Stato | Significato |
|---|---|
| `new_player` | nuovo ID, creata una nuova identità |
| `certain_external_id` | ID esterno già noto |
| `manual_confirmed` | collegamento presente nel mapping manuale |

## Revisioni

| Tipo | Significato |
|---|---|
| `homonym` | chiave del nome identica ma ID diverso |
| `possible_match` | similarità sopra soglia |
| `conflict` | mapping o dati incompatibili da risolvere |

Il fuzzy matching usa una similarità testuale deterministica. Produce candidati
con punteggio e contesto storico, ma il record conserva una nuova identità fino
a una conferma manuale.

## Mapping manuale

Il file versionabile è:

```text
data/manual-mappings/player_mappings.json
```

Ogni mapping collega una coppia provider/ID sorgente a una coppia provider/ID
già riconosciuta:

```json
{
  "source_provider": "future-list",
  "source_external_id": "ABC",
  "target_provider": "fantacalcio",
  "target_external_id": "5734",
  "note": "Confermato manualmente"
}
```

## Report locale

```powershell
python -m backend.scripts.analyze_player_matching
```

Genera:

- `reports/unmatched-players/matching-analysis.json`;
- `reports/unmatched-players/pending-reviews.csv`.

I report sono esclusi da Git. Il file di mapping manuale è invece destinato al
versionamento perché contiene decisioni controllate, non dati grezzi completi.

