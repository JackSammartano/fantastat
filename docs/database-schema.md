# Schema relazionale

## Principi

- Chiavi interne indipendenti dagli identificativi della sorgente.
- Ruoli e statistiche conservati per stagione.
- Valori originali tracciati tramite import e record sorgente.
- Hash dei file e dei record usati come chiavi di idempotenza.
- Mapping dubbi risolti in modo esplicito e auditabile.
- Squadra storica conservata come semplice associazione osservata.
- Listone corrente separato dallo storico.

## Tabelle

| Tabella | Responsabilità | Vincoli principali |
|---|---|---|
| `players` | anagrafica interna | provider + ID esterno univoci |
| `player_aliases` | nomi sorgente storici | giocatore + provider + alias univoci |
| `seasons` | stagioni | codice univoco, anni consecutivi |
| `teams` | squadre normalizzate | nome normalizzato univoco |
| `source_imports` | esecuzioni d'import | tipo + SHA-256 univoci |
| `source_records` | righe originali | riga e hash univoci nell'import |
| `player_season_stats` | storico aggregato | giocatore + stagione univoci |
| `player_team_seasons` | squadre osservate | associazione univoca |
| `player_mapping_reviews` | revisioni identità | stato e similarità controllati |
| `current_season_list` | listone 2026/2027 | stagione + record sorgente univoci |
| `ranking_configs` | ranking personalizzati | nome configurazione univoco |

## Integrità delle statistiche

Il database applica i seguenti vincoli:

- statistiche numeriche non negative;
- `penalties_taken = penalties_scored + penalties_missed`;
- con zero partite a voto, le medie analitiche devono essere `null`;
- con partite a voto positive, entrambe le medie devono essere presenti;
- almeno un record sorgente per statistica stagionale;
- ruolo Classic limitato a `P`, `D`, `C`, `A`;
- una sola riga per giocatore e stagione.

Il caso Lazetic (`Pv=0`, `Amm=1`) resta valido perché una statistica additiva
può essere positiva anche quando le medie non sono calcolabili.

## Migrazioni

Alembic usa:

```text
alembic.ini
backend/migrations/
backend/migrations/versions/
```

Il database generato non viene versionato; vengono versionati i modelli e le
migrazioni necessarie a ricrearlo.

