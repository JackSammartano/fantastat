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

## Consultazione da mobile e condivisione

L'interfaccia include navigazione mobile inferiore, filtri a colonna, tabelle
scorrevoli con prima colonna fissa e layout adattivi per schede, grafici,
ranking e revisioni.

Per condividere il progetto viene avviata una seconda istanza protetta da
password e in sola lettura:

```powershell
.\scripts\start-share.ps1 -Password "una-password-robusta"
```

Questa istanza serve la build frontend e le API sulla porta locale `8080`.
Consente il calcolo dei ranking, ma blocca salvataggi, mapping e fusioni. Per
renderla raggiungibile da Internet usare un tunnel HTTPS e arrestarlo quando
non serve. Arresto dell'istanza:

```powershell
.\scripts\stop-share.ps1
```

La modalità consigliata per la condivisione da PC aziendale è lo snapshot
pubblico GitHub Pages. Non richiede tunnel né PC acceso:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.export_static_site
```

Dettagli e procedura: `docs/github-pages.md`.

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

Il listone ufficiale viene validato e importato in modo transazionale e
idempotente:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m backend.scripts.import_current_list
```

`Tutti` è la sorgente canonica; i fogli per ruolo sono controlli di coerenza.
Il foglio `Ceduti` è contato nel report ma non entra nel listone corrente.

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
