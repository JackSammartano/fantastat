# Fantacalcio Analysis 2026/2027

Applicazione locale per analizzare quattro stagioni storiche di Fantacalcio
Serie A e preparare l'asta 2026/2027.

Include pipeline Excel read-only, normalizzazione, matching controllato,
SQLite, API FastAPI, frontend React, confronti, grafici, ranking configurabili
e revisione delle identità dubbie.

## Requisiti

- Windows e PowerShell;
- Python 3.12;
- Node.js 24 e npm;
- i quattro Excel storici nella root del progetto.

## Installazione

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

cd frontend
npm install
cd ..
```

## Prima inizializzazione

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m backend.scripts.import_seasons
```

L'importazione è idempotente. Gli Excel non vengono modificati.

## Avvio rapido

```powershell
.\scripts\start-local.ps1
```

Aprire:

- applicazione: <http://127.0.0.1:5173>;
- API Swagger: <http://127.0.0.1:8000/docs>.

Controllare o arrestare:

```powershell
.\scripts\status-local.ps1
.\scripts\stop-local.ps1
```

I servizi ascoltano esclusivamente su `127.0.0.1`. PID e log sono salvati in
`reports/runtime/`, esclusa da Git.

## Funzioni disponibili

- dashboard e riepilogo qualità;
- ricerca, filtri, ordinamento e CSV;
- storico e grafici per giocatore;
- confronto tra giocatori;
- ranking percentile con pesi manuali;
- configurazioni ranking salvabili;
- revisione dei suggerimenti fuzzy;
- fusione identità con anteprima, conflitti, backup e rollback.

Il ranking non applica preset impliciti. Affidabilità e rendimento restano
separati salvo peso esplicito dell'utente.

## Pipeline e controlli

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.inspect_excel
.\.venv\Scripts\python.exe -m backend.scripts.analyze_player_matching
.\.venv\Scripts\python.exe -m backend.scripts.validate_seasons
.\.venv\Scripts\python.exe -m backend.scripts.import_seasons
.\.venv\Scripts\python.exe -m backend.scripts.calculate_player_metrics
```

Output generati:

- report: `reports/`;
- CSV elaborati: `data/processed/`;
- database: `database/fantacalcio.db`;
- backup pre-fusione: `database/backups/`.

Queste directory generate sono escluse da Git.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest

cd frontend
npm run lint
npm test
npm run build
```

## Database

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current --check-heads
.\.venv\Scripts\alembic.exe check
```

Un database alternativo può essere configurato con
`FANTACALCIO_DATABASE_URL`.

## Listone 2026/2027

La struttura database è pronta, ma l'importazione definitiva verrà
implementata soltanto dopo l'ispezione read-only del file ufficiale.

## Documentazione

- stato operativo: `DIARIO_PROGETTO.md`;
- schema: `docs/database-schema.md`;
- dizionario dati: `docs/data-dictionary.md`;
- importazione: `docs/historical-import.md`;
- metriche: `docs/scoring-model.md`;
- ranking: `docs/ranking-proposal.md`;
- API: `docs/api.md`.

Gli Excel originali, database, report, backup e dipendenze locali non devono
essere inclusi nel repository Git.
