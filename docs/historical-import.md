# Importazione delle stagioni storiche

## Precondizioni

Prima di aprire una transazione, il comando:

1. legge gli Excel in sola lettura;
2. applica mapping e normalizzazione;
3. esegue la validazione completa;
4. interrompe l'operazione se esistono errori bloccanti o righe escluse;
5. esegue il matching senza fusioni fuzzy.

## Esecuzione

```powershell
python -m backend.scripts.import_seasons
```

Il comando utilizza il database configurato da
`FANTACALCIO_DATABASE_URL`; in assenza della variabile usa
`database/fantacalcio.db`.

## Idempotenza

Ogni workbook è identificato dal proprio SHA-256 e dal tipo di importazione. La
combinazione è protetta anche da un vincolo univoco nel database.

Se tutti i file risultano già importati, il comando restituisce
`already_imported` e non crea giocatori, statistiche, alias o revisioni.

## Transazione

La persistenza del batch avviene in una singola transazione. Un errore durante
la scrittura annulla anche le righe precedentemente inserite nello stesso batch.

## Dati salvati

- stagioni;
- identità dei giocatori;
- alias storici;
- squadre osservate come semplici valori sorgente;
- importazioni e righe raw;
- statistiche per giocatore e stagione;
- associazioni giocatore–squadra–stagione;
- warning di qualità;
- revisioni di matching pendenti.

## Output locali

- `database/fantacalcio.db`;
- `data/processed/player-season-stats.csv`;
- `reports/import-summary/import-summary.json`.

Database, CSV elaborato e report sono esclusi da Git.

