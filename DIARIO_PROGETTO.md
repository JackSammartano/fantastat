# Diario di sviluppo — Fantacalcio Serie A 2026/2027

> Documento operativo persistente per riprendere il progetto esattamente dal punto
> in cui è stato interrotto.

## Come usare questo diario

- `[ ]` attività non iniziata.
- `[-]` attività in corso.
- `[x]` attività completata e verificata.
- `[!]` attività bloccata o che richiede una decisione.
- Al termine di ogni sessione aggiornare:
  - **Stato corrente**;
  - checklist della fase;
  - file creati o modificati;
  - verifiche eseguite;
  - bug, anomalie e miglioramenti;
  - **Prossima azione esatta**.
- Non segnare una fase come completata finché i relativi criteri di accettazione
  non sono stati verificati.
- Non modificare, spostare o sovrascrivere i file Excel originali.
- Non effettuare commit Git senza una richiesta esplicita.

---

## Stato corrente

**Ultimo aggiornamento:** 7 agosto 2026
**Fase corrente:** prima versione di Fanta-Allenatore completata e verificata
localmente; modifiche non ancora committate né pubblicate

**Interfaccia asta:** il listone è la vista principale; preferiti e giocatori
acquistati possono essere gestiti dal listone e dalle schede. La nuova sezione
Fanta-Allenatore raccoglie obiettivi d'asta, rosa, budget e giornate importate.

**Mobile e condivisione:** layout responsive completo con menu FL richiudibile
in alto a destra. I dati Fanta-Allenatore sono locali e indipendenti per ogni
browser/dispositivo; non vengono inclusi nello snapshot pubblico.

**GitHub Pages:** predisposto snapshot pubblico statico dei soli 493 calciatori
attuali. Filtri, schede, confronti e ranking funzionano nel browser; dati raw,
database e operazioni amministrative restano esclusi. Deploy tramite Actions.
**Ambiente corrente:** PC aziendale, Windows, Codex CLI  
**Prossimo ambiente:** PC di casa — vedi *Migrazione al PC di casa*  
**Codice applicativo creato:** pipeline, database, API e frontend locale  
**Database creato:** sì, popolato con quattro stagioni storiche  
**Repository Git:** primo commit creato e pubblicato su
<https://github.com/JackSammartano/fantastat>, branch `main`  
**File originali modificati:** nessuno
**Servizi locali:** frontend `127.0.0.1:5173`, API `127.0.0.1:8000`

### Sessione 2026-08-07 — Fanta-Allenatore e importazione giornate

**Stato:** implementazione locale completata e verificata; pubblicazione non
ancora eseguita.

**Decisioni applicate**

- Preferiti, rosa, budget, priorità, offerte massime e note sono conservati nel
  `localStorage` del singolo browser.
- I voti, più voluminosi, sono conservati in IndexedDB nel database locale
  `fantalab-coach`.
- Il backup JSON comprende sia i dati personali sia le giornate importate.
- Gli Excel vengono letti nel browser e non caricati su API, GitHub o server.
- La sorgente predefinita è il foglio `Fantacalcio`; il parser conserva la fonte
  nell'identificativo univoco `stagione|giornata|fonte`.
- Una seconda importazione con la stessa chiave sostituisce la precedente.
- I file `Voti_Fantacalcio_Stagione_*_Giornata_*.xlsx` sono esclusi da Git.
- I voti ufficiali restano per uso personale: il workbook dichiara
  esplicitamente il divieto di riproduzione e pubblicazione su altri siti.

**Funzioni implementate**

- Nuova voce e pagina `Fanta-Allenatore` con tab Obiettivi, La mia rosa e
  Giornate.
- Aggiunta/rimozione preferito e rosa dal listone e dalla scheda giocatore.
- Priorità `alta`, `alternativa`, `scommessa`, offerta massima e note.
- Passaggio da obiettivo ad acquistato senza duplicare il calciatore.
- Budget iniziale, crediti spesi/residui e occupazione posti P/D/C/A.
- Import Excel privato con riconoscimento automatico di stagione, giornata e
  fonte, anteprima e sostituzione controllata.
- Elenco ed eliminazione delle giornate importate.
- Ultimi voti della propria rosa nella pagina Fanta-Allenatore.
- La tab `La mia rosa` usa quattro tabelle distinte per Portieri, Difensori,
  Centrocampisti e Attaccanti, con una riga per giocatore e prezzo modificabile
  direttamente in tabella.
- La vista predefinita `Complessivo` aggrega tutte le giornate importate della
  stagione e fonte più recenti: presenze, media voto, gol, assist, gol subiti,
  rigori parati, ammonizioni ed espulsioni.
- Il selettore `Vista statistiche` permette di sostituire l'aggregato con i
  dati di una singola giornata mantenendo la medesima struttura per ruolo.
- Aggiunte le colonne `Forma 5` e `Trend recente`. Forma 5 è la media degli
  ultimi cinque voti validi disponibili; le giornate senza voto non diventano
  zero. Il trend è la pendenza della regressione lineare sugli stessi ultimi
  cinque voti, in ordine cronologico, con minimo tre osservazioni.
- Soglie del trend giornata: freccia su per pendenza arrotondata almeno
  `+0,10` punti per voto, freccia giù per valore al massimo `-0,10`, freccia
  orizzontale nell'intervallo intermedio. Il numero viene sempre mostrato
  accanto alla freccia; con tre o quattro voti compare `campione ridotto`.
- Quando si consulta una giornata passata, gli eventi della tabella sono solo
  quelli di quel turno, mentre Forma 5 e Trend usano esclusivamente i voti
  importati fino a quella giornata, senza informazioni future.
- Prima degli import la rosa resta interamente visibile con statistiche vuote
  e un collegamento diretto a `Importa giornata`.
- Storico dei voti importati nella scheda del singolo calciatore.
- Navigazione contestuale dalle schede: un giocatore aperto dagli Obiettivi
  torna a `Fanta-Allenatore > Obiettivi`; se aperto dalla rosa torna a
  `Fanta-Allenatore > La mia rosa`, senza reindirizzamento al listone.
- Esportazione e ripristino del backup completo.
- Centratura corretta dei pulsanti compatti preferito/rosa nel listone tramite
  area interattiva quadrata 40x40 pixel.
- Le card della tab `Obiettivi` hanno dimensioni uniformi e una griglia che non
  espande le poche card presenti: quattro colonne su desktop, tre su tablet,
  due sui dispositivi compatti e una sotto i 520 pixel. La progressione
  preserva leggibilità e assenza di scorrimento orizzontale su mobile.
- Tabelle `La mia rosa` rese più compatte: badge del ruolo presente soltanto
  nel titolo del reparto e con lettera bianca, colonna `Rigori parati` rimossa,
  spaziature e larghezze riequilibrate per limitare lo scorrimento orizzontale.
- La colonna `Gol subiti` è riservata alla tabella Portieri; per i portieri le
  statistiche finali seguono l'ordine Gol subiti, Amm., Esp., Gol, Assist,
  mentre negli altri reparti restano Gol, Assist, Amm. ed Esp.
- Il listone non mostra più Quotazione Mantra, FVM Classic e FVM Mantra: al
  loro posto espone quotazione Classic iniziale e variazione, più utili per
  leggere l'evoluzione del valore. Dashboard e ordinamenti rapidi usano ora la
  quotazione Classic; il menu Fanta-Allenatore apre direttamente `La mia rosa`.
- Aggiunto il pulsante `Aggiorna listone` direttamente nella pagina Listone
  26/27; la funzione è stata rimossa da Fanta-Allenatore. Importa nel browser
  il foglio ufficiale `Tutti`, valida stagione/intestazioni/variazioni, mostra anteprima
  di nuovi, usciti e modificati e aggiorna listone, dashboard, schede e ranking.
  Il collegamento allo storico usa esclusivamente l'ID Fantacalcio; rosa e
  obiettivi vengono riconciliati e il listone locale entra nel backup completo.
- `Aggiorna listone` apre direttamente il selettore Excel, senza un pannello
  intermedio; il pannello compare solo durante la lettura e per anteprima,
  errori, conferma o ripristino.
- Il controllo `Rendimento della rosa` è stato compattato in una singola riga
  su desktop, con titolo, vista attiva e selettore; su mobile torna a capo per
  mantenere il controllo facilmente utilizzabile.
- Suite importazioni ampliata con fixture sintetiche prive di dati protetti:
  parser listone valido e casi di foglio assente, variazione incoerente, ID
  duplicato e ruolo invalido; riconciliazione di noti, nuovi e usciti; parser
  giornate con fonte, squadra, senza voto e righe allenatore; persistenza,
  ordinamento, sostituzione ed eliminazione in IndexedDB; persistenza, filtri e
  ripristino del listone locale. Esito: 31 test frontend e 89 backend superati,
  lint pulito e build statica completata.

**Collaudo sul file reale**

File: `Voti_Fantacalcio_Stagione_2025_26_Giornata_38.xlsx`.

- Tre fogli riconosciuti: `Fantacalcio`, `Statistico`, `Italia`.
- Titolo rilevato: `Voti Fantacalcio 38ª giornata di campionato`.
- Stagione rilevata: `2025/2026`.
- Giornata rilevata: `38`.
- 340 righe numeriche nel foglio: 320 calciatori e 20 allenatori con ruolo
  speciale `ALL`.
- Le 20 righe allenatore vengono escluse esplicitamente e conteggiate
  nell'anteprima; non sono perse silenziosamente.

**File principali creati**

```text
frontend/src/coach/types.ts
frontend/src/coach/CoachContext.tsx
frontend/src/coach/matchdayStore.ts
frontend/src/coach/matchdayParser.ts
frontend/src/coach/matchdayParser.test.ts
frontend/src/components/CoachPlayerActions.tsx
frontend/src/pages/FantaCoachPage.tsx
```

**File principali modificati**

```text
.gitignore
frontend/package.json
frontend/package-lock.json
frontend/src/App.tsx
frontend/src/main.tsx
frontend/src/components/AppShell.tsx
frontend/src/pages/CurrentListPage.tsx
frontend/src/pages/PlayerDetailPage.tsx
frontend/src/styles.css
DIARIO_PROGETTO.md
```

**Verifiche**

```text
Vitest: 13 test superati su 13 in 5 file
ESLint: superato senza errori o warning
TypeScript + build statica Vite: superati
Parser JavaScript sul workbook reale: foglio Fantacalcio e 320 giocatori
git check-ignore: file Voti della giornata correttamente ignorato
```

Verifica ripetuta dopo l'introduzione della rosa tabellare e del trend sulle
giornate: 16 test superati in 6 file, ESLint e build statica superati.

**Dipendenze**

- Aggiunto `read-excel-file` 9.3.5 per la lettura privata degli `.xlsx` nel
  browser.
- `npm install` segnala quattro vulnerabilità high; non è stato eseguito alcun
  `npm audit fix` automatico. FE-002 resta aperto per audit controllato.

**Prossima azione esatta**

1. eseguire un collaudo manuale nel browser con preferito, acquisto, budget e
   importazione della giornata 38;
2. verificare visivamente mobile e desktop;
3. se approvato dall'utente, creare commit e pubblicare su GitHub Pages;
4. in una fase successiva aggiungere regole bonus/malus configurabili e
   fantavoto calcolato.

### Migrazione al PC di casa

Il repository Git **non** contiene i dati: Excel, database, report e
`data/processed/` restano esclusi per decisione approvata. Vanno trasferiti a
mano, ad esempio via chiavetta USB.

**Da trasferire fuori da Git**

| File | Dimensione | Necessario? |
|---|---:|---|
| `Statistiche_Fantacalcio_Stagione_2022_23.xlsx` | ~90 KB | sì |
| `Statistiche_Fantacalcio_Stagione_2023_24.xlsx` | ~90 KB | sì |
| `Statistiche_Fantacalcio_Stagione_2024_25.xlsx` | ~90 KB | sì |
| `Statistiche_Fantacalcio_Stagione_2025_26.xlsx` | ~90 KB | sì |
| `database/fantacalcio.db` | ~1,9 MB | consigliato |

Gli Excel vanno collocati nella root del progetto. Senza di essi l'importazione
non è eseguibile e l'applicazione resta vuota.

Il database è interamente rigenerabile dagli Excel, quindi non è strettamente
necessario. Trasferirlo conserva però le cinque revisioni di matching già
risolte, che **non** sono replicabili da file versionati: si veda l'anomalia
MAP-002 più sotto.

**Prerequisiti sul PC di casa**

- Python 3.12;
- Node.js 24 e npm;
- Git configurato con identità personale.

**Sequenza di ripristino**

```powershell
git clone https://github.com/JackSammartano/fantastat.git
cd fantastat
# copiare qui i quattro .xlsx e, se trasferito, database/fantacalcio.db
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cd frontend
npm install
cd ..
```

Se il database **non** è stato trasferito, rigenerarlo:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m backend.scripts.import_seasons
```

Se il database **è** stato trasferito, verificare soltanto l'allineamento:

```powershell
.\.venv\Scripts\alembic.exe current --check-heads
```

### Prossima azione esatta

Alla prossima sessione, sul PC di casa:

1. rileggere questo diario;
2. completare la *Sequenza di ripristino* qui sopra;
3. eseguire `.venv\Scripts\python.exe -m pytest`;
4. eseguire `alembic current --check-heads` e `alembic check`;
5. configurare l'identità Git personale del PC di casa;
6. svolgere l'audit npm controllato per FE-002, senza `--force`;
7. verificare lo stato reale delle revisioni di matching: attese cinque
   `resolved` con esito `new_player` e una `pending`, l'omonimo `Ndiaye`;
8. decidere come trattare MAP-002, cioè la mancata persistenza delle decisioni
   `new_player` nel file di mapping versionato;
9. esaminare la revisione pendente senza confermare fusioni automatiche;
10. verificare l'export `data/processed/player-metrics.csv`;
11. non applicare fusioni reali senza verifica umana dei singoli calciatori;
12. esporre il listone corrente tramite API e frontend nella prossima fase;
13. integrare i trigger d'importazione API soltanto se richiesto.

---

## Obiettivo

Costruire un'applicazione locale per:

- importare quattro stagioni storiche di Fantacalcio Serie A;
- normalizzare e validare i dati senza perdere i valori originali;
- mantenere statistiche, ruoli e squadre separati per stagione;
- collegare in modo controllato le identità dei giocatori;
- integrare successivamente il listone ufficiale 2026/2027;
- consultare storico, confronti, grafici e classifiche configurabili;
- supportare la preparazione dell'asta senza presentare una metrica arbitraria
  come verità assoluta.

---

## Decisioni approvate

- [x] Backend e pipeline dati in Python.
- [x] Lettura Excel con `pandas` e `openpyxl`.
- [x] Database locale SQLite, da creare in una fase successiva sul PC di casa.
- [x] API REST con FastAPI.
- [x] Frontend React, TypeScript e Vite.
- [x] Grafici con Recharts.
- [x] Tabelle con TanStack Table.
- [x] Test automatici con pytest.
- [x] `Tutti` sarà la sorgente canonica dei dati.
- [x] I fogli per ruolo saranno usati come controllo di coerenza.
- [x] Gli Excel originali saranno considerati in sola lettura.
- [x] Gli Excel originali saranno esclusi da Git.
- [x] `Id` sarà l'identificativo esterno principale, ma il database utilizzerà
  anche un `player_id` interno.
- [x] Il nome visualizzato non sarà usato come identificatore definitivo.
- [x] Il fuzzy matching produrrà soltanto suggerimenti e non fusioni automatiche.
- [x] Ruolo Classic e ruoli Mantra saranno conservati per singola stagione.
- [x] `Squadra` è un semplice valore sorgente proveniente dal dataset.
- [x] Non verrà attribuita a `Squadra` la semantica di squadra finale, squadra
  prevalente o squadra relativa a una porzione specifica delle statistiche.
- [x] La pipeline conserverà il valore originale di `Squadra`.
- [x] Quando `Pv = 0`, gli zeri sorgente di `Mv` e `Fm` saranno conservati ma i
  corrispondenti valori analitici saranno `null`.
- [x] L'assenza di un giocatore da una stagione sarà `null`, non zero.
- [x] Ranking e affidabilità saranno configurabili e documentati prima
  dell'implementazione delle formule.
- [x] Nessun commit Git sarà eseguito senza richiesta esplicita.

### Decisioni ancora aperte

- [ ] Confermare tramite documentazione della fonte il significato esatto di
  `Pv`, `Mv`, `Fm`, `Gf`, `Gs`, `Rp`, `Rc`, `R+`, `R-`, `Ass`, `Amm`, `Esp`,
  `Au`.
- [ ] Decidere se Git debba essere inizializzato prima o dopo la fase 1.
- [ ] Approvare le formule delle metriche derivate.
- [ ] Approvare la formula dell'indicatore sintetico di affidabilità, se verrà
  introdotto.
- [ ] Approvare le configurazioni iniziali dei ranking per ruolo.
- [ ] Analizzare il listone ufficiale 2026/2027 quando sarà disponibile.

---

## Dataset disponibili

| Stagione | File | Righe in `Tutti` | Stato |
|---|---|---:|---|
| 2022/2023 | `Statistiche_Fantacalcio_Stagione_2022_23.xlsx` | 672 | analizzato |
| 2023/2024 | `Statistiche_Fantacalcio_Stagione_2023_24.xlsx` | 664 | analizzato |
| 2024/2025 | `Statistiche_Fantacalcio_Stagione_2024_25.xlsx` | 679 | analizzato |
| 2025/2026 | `Statistiche_Fantacalcio_Stagione_2025_26.xlsx` | 663 | analizzato |

### Struttura verificata

- [x] Quattro workbook individuati.
- [x] Cinque fogli per workbook:
  `Tutti`, `Portieri`, `Difensori`, `Centrocampisti`, `Attaccanti`.
- [x] Titolo alla riga 1 con celle `A1:R1` unite.
- [x] Intestazioni reali alla riga 2.
- [x] Diciotto colonne identiche in tutte le stagioni.
- [x] Nessuna formula.
- [x] Nessuna colonna interamente vuota.
- [x] Nessun valore null nel dataset sorgente.
- [x] Nessuna riga esattamente duplicata.
- [x] Nessun ID duplicato all'interno della stessa stagione.
- [x] Nessun nome duplicato all'interno della stessa stagione.
- [x] Nessun numero negativo.
- [x] I fogli per ruolo contengono gli stessi ID del relativo sottoinsieme di
  `Tutti`.

### Colonne sorgente verificate

```text
Id, R, Rm, Nome, Squadra, Pv, Mv, Fm, Gf, Gs,
Rp, Rc, R+, R-, Ass, Amm, Esp, Au
```

### Conteggi per ruolo

| Stagione | Portieri | Difensori | Centrocampisti | Attaccanti |
|---|---:|---:|---:|---:|
| 2022/2023 | 76 | 239 | 232 | 125 |
| 2023/2024 | 72 | 229 | 223 | 140 |
| 2024/2025 | 83 | 239 | 226 | 131 |
| 2025/2026 | 75 | 232 | 217 | 139 |

### Identità dei giocatori

- Record storici complessivi: **2.678**.
- ID distinti: **1.334**.
- Presenti in una stagione: **592**.
- Presenti in due stagioni: **337**.
- Presenti in tre stagioni: **208**.
- Presenti in tutte e quattro: **197**.
- ID con più varianti del nome: **18**.
- ID con cambio di ruolo Classic: **18**.
- Nome identico associato a ID differenti: `Ndiaye`, ID `5859` e `7202`.

Esempi di alias già rilevati:

```text
D'Alessandro / D'alessandro
D'Ambrosio / D'ambrosio
Kouame' / Kouamè
Rafael Leao / Leao
Mari' / Marì
Montipo' / Montipò
McKennie / Mckennie
Soule' / Soulè
Dodo' / Dodò
Lucumi' / Lucumì
Lauriente' / Laurientè
Buchanan / Buchanan T.
```

### Trasferimenti e squadra

- [x] Ogni giocatore compare al massimo una volta per stagione.
- [x] Non esistono righe separate per più squadre nella stessa stagione.
- [x] Non esiste una combinazione riga-per-squadra più riga totale.
- [x] Il campo `Squadra` sarà conservato come valore sorgente senza inferenze.
- [ ] Verificare se futuri dataset introducono righe multiple per squadra.

### Anomalie note

#### DQ-001 — Ammonizione con zero presenze valide

```text
Stagione: 2022/2023
Id: 5785
Nome: Lazetic
Squadra: Milan
Pv: 0
Amm: 1
```

Stato: warning, non errore bloccante. La riga non deve essere eliminata.

#### DQ-002 — Zeri usati come valori sentinella

Record con `Pv = 0`:

| Stagione | Record |
|---|---:|
| 2022/2023 | 125 |
| 2023/2024 | 120 |
| 2024/2025 | 118 |
| 2025/2026 | 116 |

Regola approvata:

- conservare `Pv = 0`;
- conservare gli zeri sorgente;
- normalizzare `Mv` e `Fm` analitiche a `null`;
- impostare `has_valid_rating = false`.

#### DQ-003 — Omonimo

`Ndiaye` è associato agli ID esterni `5859` e `7202`. Non unire in automatico.

---

## Modello dati approvato come base progettuale

### Entità

- [ ] `players`
- [ ] `player_aliases`
- [ ] `seasons`
- [ ] `teams`
- [ ] `source_imports`
- [ ] `source_records`
- [ ] `player_season_stats`
- [ ] `player_team_seasons`
- [ ] `player_mapping_reviews`
- [ ] `current_season_list`
- [ ] `ranking_configs`

### Vincoli essenziali

- [ ] `seasons.code` univoco.
- [ ] `players.external_player_id` univoco per provider, quando presente.
- [ ] `player_season_stats` univoco per giocatore e stagione.
- [ ] `source_imports` idempotente tramite tipo import e SHA-256.
- [ ] `source_records` tracciabile tramite import, foglio, riga e hash.
- [ ] Il nome normalizzato non deve essere univoco.
- [ ] Le decisioni manuali di matching devono essere persistenti e auditabili.
- [ ] Il listone 2026/2027 deve conservare ruolo e squadra separati dallo storico.

---

# Piano di sviluppo

## Fase 0 — Analisi iniziale

**Stato:** completata.

- [x] Esaminare la root del progetto.
- [x] Individuare tutti i file disponibili.
- [x] Individuare i quattro Excel.
- [x] Analizzare workbook e fogli.
- [x] Rilevare intestazioni e tipi.
- [x] Confrontare le stagioni.
- [x] Controllare formule e celle unite.
- [x] Controllare null e duplicati.
- [x] Verificare ID esterni.
- [x] Analizzare collisioni ID/nome.
- [x] Verificare rappresentazione delle squadre.
- [x] Identificare cambi di ruolo.
- [x] Proporre architettura.
- [x] Proporre modello dati.
- [x] Proporre piano di implementazione.

**File modificati:** solo questo diario, creato dopo l'approvazione.  
**Verifica:** rileggere le sezioni Dataset, Decisioni e Anomalie.

### Bug/miglioramenti della fase

- Miglioramento: automatizzare tutti i controlli tramite uno script ripetibile.
- Miglioramento: aggiungere hash SHA-256 dei workbook al report.
- Decisione aperta: reperire il dizionario ufficiale delle abbreviazioni.

---

## Fase 1 — Ispezione Excel ripetibile

**Stato:** completata e verificata il 27 luglio 2026.

### File autorizzati per questa fase

```text
.gitignore
pyproject.toml
README.md
backend/__init__.py
backend/config/seasons.yaml
backend/scripts/__init__.py
backend/scripts/inspect_excel.py
backend/tests/__init__.py
backend/tests/test_inspect_excel.py
backend/tests/fixtures/.gitkeep
docs/import-process.md
reports/.gitkeep
```

### Task

- [x] Creare la struttura minima autorizzata.
- [x] Configurare le quattro stagioni senza percorsi assoluti.
- [x] Leggere gli Excel esclusivamente in modalità read-only.
- [x] Rilevare fogli, dimensioni, intestazioni e tipi.
- [x] Rilevare formule, celle unite e righe introduttive.
- [x] Rilevare null, duplicati e colonne vuote.
- [x] Verificare `Tutti` contro i fogli per ruolo.
- [x] Rilevare collisioni tra ID e nomi.
- [x] Rilevare cambi di ruolo e squadra.
- [x] Rilevare valori sentinella e intervalli anomali.
- [x] Calcolare SHA-256 dei file.
- [x] Generare report JSON e Markdown deterministici.
- [x] Aggiungere test con fixture sintetiche.
- [x] Documentare il comando Windows per l'ispezione.

### Criteri di accettazione

- [x] Nessun Excel originale viene modificato.
- [x] Due esecuzioni producono lo stesso contenuto a parità di input.
- [x] I conteggi coincidono con quelli annotati in questo diario.
- [x] DQ-001, DQ-002 e DQ-003 sono rilevati dall'ispettore e dai relativi dati
  cross-stagione.
- [x] Tutti i test passano: 4 test su 4 con pytest 8.4.2.

### File creati

```text
.gitignore
pyproject.toml
README.md
backend/__init__.py
backend/config/seasons.yaml
backend/scripts/__init__.py
backend/scripts/inspect_excel.py
backend/tests/__init__.py
backend/tests/test_inspect_excel.py
backend/tests/fixtures/.gitkeep
docs/import-process.md
reports/.gitkeep
reports/data-quality/excel-inspection.json
reports/data-quality/excel-inspection.md
```

Gli ultimi due file sono generati e ignorati da Git.

### Verifiche eseguite

```text
python -m pytest
Risultato: 4 passed in 0.48s

python -m backend.scripts.inspect_excel
Risultato: 4 workbook analizzati
```

Il report reale conferma:

- 2.678 record;
- 1.334 ID esterni;
- 18 ID con varianti del nome;
- 18 ID con cambio ruolo;
- una collisione nome–ID (`Ndiaye`);
- DQ-001 per Lazetic.

### Bug/miglioramenti

- Risolto: `pytest` non era presente ed è stato installato su autorizzazione
  esplicita.
- Miglioramento applicato: rimossa la dipendenza da `PyYAML`; il file
  `seasons.yaml` usa sintassi JSON, sottoinsieme valido di YAML, ed è leggibile
  con la libreria standard.
- Miglioramento futuro: aggiungere un test esplicito che confronti l'intero
  contenuto delle righe fra `Tutti` e i fogli per ruolo, non soltanto gli ID.

---

## Fase 2 — Dizionario dati e mapping colonne

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Verificare il significato delle abbreviazioni tramite dati e pagine
  ufficiali disponibili.
- [x] Definire nomi canonici delle colonne.
- [x] Definire tipo, nullabilità e dominio di ogni campo.
- [x] Configurare un mapping condiviso dalle quattro stagioni.
- [x] Configurare valori nulli e sentinella.
- [x] Configurare ruoli Classic e Mantra.
- [x] Configurare squadre senza inferirne la semantica.
- [x] Scrivere `docs/data-dictionary.md`.
- [x] Testare intestazioni mancanti, duplicate o inattese.

### Criteri di accettazione

- [x] Ogni significato registra lo stato dell'evidenza: ufficiale, verificato
  dai dati o confermato dall'utente.
- [x] Le quattro stagioni condividono un mapping esplicito e versionato.
- [x] Colonne mancanti, inattese o duplicate sono segnalate esplicitamente.
- [x] Le intestazioni reali delle quattro stagioni sono valide e nello stesso
  ordine del mapping.

### Bug/miglioramenti

- Aggiunti 9 test dedicati; suite complessiva: 13 test superati.
- `Rc = R+ + R-` è documentata come relazione verificata su 2.678 record.
- Il mapping rinomina soltanto i campi: conversione e normalizzazione restano
  intenzionalmente nella fase 5.
- Miglioramento futuro: quando sarà disponibile il file 2026/2027, creare un
  mapping separato se presenta colonne differenti.

---

## Fase 3 — Repository Git e ambiente di sviluppo

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Approvare il momento dell'inizializzazione Git.
- [x] Inizializzare Git.
- [x] Applicare `.gitignore`.
- [x] Verificare che gli Excel non siano tracciati.
- [x] Configurare ambiente virtuale Python.
- [x] Bloccare le versioni principali in `pyproject.toml`.
- [ ] Configurare linting e type checking essenziali in una fase dedicata.
- [x] Documentare setup Windows.
- [x] Non eseguire commit senza richiesta esplicita.

### Bug/miglioramenti

- `.venv`, database, report, Excel ed `*.egg-info` risultano ignorati.
- `prompt.txt` è stato successivamente escluso da Git su richiesta esplicita:
  il file resta sul disco locale ma non è più versionato né pubblicato.
- Aggiornamento del 27 luglio 2026: su richiesta esplicita dell'utente sono
  stati creati il primo commit e il repository remoto. Si veda la sessione
  *Primo commit e pubblicazione su GitHub*.

---

## Fase 4 — Modello relazionale e database

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Trasformare il modello concettuale approvato in schema SQLAlchemy.
- [x] Implementare relazioni, chiavi e vincoli.
- [x] Configurare SQLite.
- [x] Configurare Alembic.
- [x] Creare la migrazione iniziale.
- [x] Testare vincoli e relazioni.
- [x] Escludere database generati da Git.

### Criteri di accettazione

- [x] Nessun duplicato giocatore-stagione.
- [x] Import e record sorgente sono tracciabili.
- [x] Il modello distingue assenza, zero e valore non calcolabile.
- [x] Ruoli e squadre restano separati per stagione.
- [x] La migrazione crea correttamente un database vuoto.
- [x] Database alla revisione `d37bd727689e (head)`.
- [x] `alembic check`: nessuna operazione nuova rilevata.

### Bug/miglioramenti

- Risolto DB-001: il `PRAGMA foreign_keys=ON` apriva una transazione implicita
  prima di Alembic. Il DDL restava, ma la riga `alembic_version` veniva
  annullata. Ora il PRAGMA viene confermato prima della migrazione.
- Il database errato, vuoto e interamente generato è stato eliminato e ricreato.
- Aggiunti 7 test database; suite complessiva: 20 test superati.
- Miglioramento futuro: aggiungere un test di migrazione completo upgrade,
  downgrade e nuovo upgrade su file temporaneo.

---

## Fase 5 — Normalizzazione

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Normalizzare Unicode.
- [x] Normalizzare spazi e maiuscole/minuscole.
- [x] Gestire apostrofi e accenti.
- [x] Conservare nome e squadra originali.
- [x] Gestire numeri con virgola italiana.
- [x] Gestire percentuali soltanto quando esplicitamente ammesse.
- [x] Gestire celle vuote, `-`, `N.D.` e `n/a`.
- [x] Normalizzare ruoli Classic e Mantra.
- [x] Trasformare `Mv/Fm = 0` in `null` quando `Pv = 0`.
- [x] Non trasformare stagioni mancanti in record a zero.
- [x] Aggiungere test unitari.

### Bug/miglioramenti

- La pipeline mantiene tre livelli distinti: raw, canonico e analitico.
- La chiave senza accenti è soltanto un ausilio al matching.
- Non sono stati inventati alias di squadra.
- Prova reale: 2.678 record normalizzati, zero errori.
- 479 record con medie analitiche `null` e valori sorgente preservati.
- Suite complessiva: 37 test superati.
- Miglioramento futuro: aggiungere una configurazione manuale degli alias squadra
  soltanto quando emergeranno differenze reali.

---

## Fase 6 — Matching dei giocatori

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Collegare prima tramite ID esterno.
- [x] Raccogliere tutte le varianti come alias dell'identità.
- [x] Gestire mapping manuali JSON versionabili.
- [x] Rilevare omonimi.
- [x] Generare candidati tramite nome normalizzato e contesto.
- [x] Aggiungere fuzzy matching solo come suggerimento.
- [x] Non fondere automaticamente casi ambigui.
- [x] Registrare punteggio, motivazione e decisione.
- [x] Testare `Ndiaye` come caso di omonimia.
- [x] Verificare le 18 identità con varianti del nome.
- [x] Testare i cambi ruolo e squadra come semplice contesto.

### Bug/miglioramenti

- Analizzati 2.678 record e create 1.334 identità.
- 1.344 record collegati con ID esterno certo.
- 1.334 prime occorrenze registrate come nuove identità.
- 18 identità raccolgono più alias.
- Revisioni: un omonimo e cinque possibili corrispondenze.
- Nessuna fusione fuzzy o basata sul nome.
- Suite complessiva: 44 test superati.
- Miglioramento futuro: la pagina frontend di revisione userà lo stesso formato
  del mapping manuale.

---

## Fase 7 — Validazione e qualità dei dati

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Definire errori bloccanti.
- [x] Definire warning.
- [x] Verificare intervalli plausibili.
- [x] Verificare valori negativi.
- [x] Verificare coerenza `Rc = R+ + R-`.
- [x] Verificare `Pv`, medie e statistiche additive.
- [x] Segnalare duplicati giocatore-stagione.
- [x] Segnalare conversioni fallite.
- [x] Segnalare righe escluse.
- [x] Produrre conteggi iniziali e finali.
- [x] Generare report separati per categoria.

### Bug/miglioramenti

- Regole configurate in `backend/config/validation_rules.yaml`.
- Il limite `Pv<=38` deriva dalle giornate delle stagioni analizzate.
- Nessun limite arbitrario applicato alla fantamedia.
- Validazione reale: zero errori bloccanti e zero esclusioni.
- Un warning: Lazetic, `Pv=0` e un'ammonizione.
- Riconciliazione: 2.678 sorgente = 2.678 normalizzate + 0 escluse.
- Suite complessiva: 52 test superati.

---

## Fase 8 — Importazione idempotente

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Calcolare hash del file.
- [x] Registrare `source_imports`.
- [x] Registrare `source_records`.
- [x] Usare transazioni.
- [x] Evitare duplicazioni alla seconda esecuzione.
- [x] Gestire file già importati senza riscritture.
- [x] Salvare SQLite.
- [x] Esportare CSV elaborato.
- [x] Salvare report di importazione.
- [x] Testare importazione ripetuta.
- [x] Testare rollback in caso di errore di persistenza.

### Bug/miglioramenti

- Prima esecuzione: 4 file e 2.678 righe importate.
- Seconda esecuzione: stato `already_imported`, zero righe create.
- Database: 1.334 giocatori, 1.352 alias, 4 stagioni, 27 squadre.
- Salvati 2.678 record sorgente e 2.678 record statistici.
- Salvate 2.678 associazioni squadra osservata.
- Salvati un warning qualità e 6 mapping review pendenti.
- Export CSV: 2.678 righe.
- Testato rollback totale di un batch con hash record duplicato.
- Suite complessiva: 56 test superati.
- Miglioramento futuro: conservare separatamente lo storico dei riepiloghi di
  ogni esecuzione, oltre all'ultimo `import-summary.json`.

---

## Fase 9 — Metriche storiche e affidabilità

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Definire formule disponibili.
- [x] Mostrare le formule prima dell'implementazione.
- [x] Ricevere approvazione esplicita.
- [x] Media semplice tra stagioni disponibili.
- [x] Media ponderata per `Pv`.
- [x] Non dichiarare una ponderazione per voti validi non disponibili.
- [x] Ultima stagione.
- [x] Ultime due stagioni.
- [x] Variazioni percentuali con gestione del denominatore zero.
- [x] Gol e assist per presenza valida.
- [x] Continuità e volatilità.
- [x] Dimensione del campione.
- [x] Stagioni disponibili.
- [x] Presenze recenti.
- [x] Shrinkage piccoli campioni soltanto come metrica separata.
- [x] Testare tutte le formule.

### Bug/miglioramenti

- Metriche calcolate per 1.334 giocatori.
- 218 giocatori senza fantamedia ponderabile, correttamente `null`.
- Fasce: 268 alta, 258 media, 808 bassa.
- Suite complessiva: 63 test superati.
- Miglioramento futuro: permettere a API e frontend di sovrascrivere decay,
  soglia continuità e `K` senza cambiare i default.

---

## Fase 10 — API FastAPI

**Stato:** API core completate e verificate il 27 luglio 2026; ranking e trigger
import rinviati alle fasi funzionali dedicate.

- [x] Configurare FastAPI e modelli di risposta coerenti.
- [x] `GET /api/v1/seasons`
- [x] `GET /api/v1/players`
- [x] `GET /api/v1/players/{id}`
- [x] `GET /api/v1/players/{id}/history`
- [x] `GET /api/v1/players/compare`
- [ ] `GET /api/v1/rankings`
- [ ] `POST /api/v1/rankings/calculate`
- [ ] CRUD configurazioni ranking.
- [x] `GET /api/v1/data-quality/issues`
- [x] `GET /api/v1/player-mappings/pending`
- [x] `POST /api/v1/player-mappings/{id}/resolve`
- [ ] Endpoint import stagioni.
- [ ] Endpoint import listone corrente.
- [x] Filtri e paginazione.
- [x] Validazione input.
- [x] Errori senza stack trace.
- [x] OpenAPI.
- [x] Test API.

### Bug/miglioramenti

- 71 test superati.
- Smoke test reale: 4 stagioni, 1.334 giocatori, 7 issue e 6 mapping pendenti.
- API vincolata a `127.0.0.1` nel comando documentato.
- CORS consentito soltanto al frontend locale su porta 5173.
- Warning noto API-001: FastAPI/Starlette segnala la futura deprecazione del
  TestClient basato su `httpx`; i test passano e non influenza il runtime.
- Ranking e import via HTTP restano intenzionalmente non esposti.

---

## Fase 11 — Frontend base

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Inizializzare React, TypeScript e Vite.
- [x] Configurare client API.
- [x] Creare layout responsivo.
- [x] Dashboard.
- [x] Elenco giocatori.
- [x] Ricerca per nome.
- [x] Filtri per ruolo, squadra, stagioni e presenze.
- [x] Ordinamento.
- [x] Selezione colonne.
- [x] Paginazione.
- [x] Esportazione CSV della pagina corrente.
- [x] Indicatore di affidabilità.
- [x] Dettaglio giocatore.
- [x] Grafici storici con Recharts.
- [x] Stati loading, empty ed error.
- [x] Test essenziali.

### Bug/miglioramenti

- Lint completato senza errori.
- 3 test frontend superati; 71 test backend superati.
- Build di produzione completata.
- Warning di build: bundle JavaScript da circa 695 kB; introdurre lazy loading
  e separazione dei grafici prima della distribuzione.
- I font sono esclusivamente locali/di sistema: il browser non contatta servizi
  font esterni.
- L'export CSV riguarda intenzionalmente la pagina caricata, come indicato dal
  pulsante; un export completo richiederà un endpoint dedicato.
- Filtro squadra implementato come valore testuale esatto perché `Squadra`
  rimane un valore sorgente; non viene attribuita alcuna semantica ulteriore.
- Suite frontend aggiornata: 4 test superati.

---

## Fase 12 — Confronti e classifiche configurabili

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Selezione di più giocatori.
- [x] Confronto storico.
- [x] Confronto medie ponderate.
- [x] Confronto ultima stagione.
- [x] Confronto affidabilità.
- [x] Selezione ruolo.
- [x] Soglia minima di presenze.
- [x] Selezione stagioni.
- [x] Pesi delle metriche.
- [x] Peso temporale delle stagioni recenti.
- [x] Configurazioni salvabili.
- [x] Composizione trasparente del punteggio.
- [x] Test ranking e casi limite.

### Bug/miglioramenti

- Pagina confronto limitata a quattro giocatori per leggibilità; l'API ne
  supporta fino a dieci.
- Aggiunto lazy loading delle pagine: Recharts non fa più parte del bundle
  iniziale della dashboard.
- Formula ranking approvata e documentata in `docs/ranking-proposal.md`.
- Nessun preset: tutti i pesi attivi provengono dalla richiesta dell'utente.
- I giocatori con una metrica pesata mancante vengono esclusi e conteggiati.
- Configurazioni persistite nella tabella locale `ranking_configs`.
- Prestazione reale ottimizzata da circa 4,3 secondi a circa 0,32 secondi per
  un ranking dei centrocampisti sulle quattro stagioni.
- Verifica finale: 6 test frontend e 80 test backend superati; lint e build
  completati.
- Bundle iniziale ridotto da circa 696 kB a circa 235 kB; grafici caricati in
  chunk separato.

---

## Fase 13 — Revisione delle corrispondenze

**Stato:** completata e verificata il 27 luglio 2026.

- [x] Elenco mapping pendenti.
- [x] Dati sorgente e candidati.
- [x] Punteggio di similarità.
- [x] Contesto di squadra e ruolo.
- [x] Conferma candidato come decisione di audit.
- [x] Conferma mantenimento nuova identità.
- [x] Scarto del suggerimento senza eliminare dati.
- [x] Persistenza della decisione.
- [x] Audit delle decisioni.
- [x] Test di conflitti e omonimi.
- [x] Fusione/ricollocazione controllata dello storico già importato.
- [x] Scrittura della decisione nel file di mapping manuale.
- [x] Anteprima con token legato allo stato.
- [x] Blocco per sovrapposizioni stagionali e conflitti alias.
- [x] Backup SQLite locale prima dell'applicazione.
- [x] Audit persistente e annullamento della fusione.

### Bug/miglioramenti

- Ogni azione richiede conferma esplicita nel browser.
- Nessuna delle sei revisioni reali è stata modificata durante sviluppo e test.
- Le azioni `new_player` ed `exclude` sono formulate in modo da chiarire che
  non cancellano righe storiche.
- La fusione richiede anteprima, digitazione `FONDI` e seconda conferma.
- Anteprime reali: 4 casi bloccati; `Pavoletti/Paoletti` e
  `Braschi/Biraschi` tecnicamente fondibili ma sospetti falsi positivi.
- Nessuna fusione reale applicata: `player_merge_audits` resta a 0.
- Verifica: 8 test frontend e 82 test backend superati; lint, build e Alembic
  check completati.

**Rettifica del 27 luglio 2026.** Questa sezione dichiarava in precedenza
"6 revisioni pendenti" e "nessuna delle sei revisioni reali è stata modificata".
L'ispezione diretta del database smentisce l'affermazione: cinque revisioni
risultano `resolved` fra le 12:03 e le 12:05 del 27 luglio 2026, tutte con
esito `new_player` e autore `local-user`.

| id | tipo | similarità | stato | esito |
|---:|---|---:|---|---|
| 1 | possible_match | 94,12 | resolved | new_player |
| 2 | possible_match | 92,31 | resolved | new_player |
| 3 | possible_match | 94,12 | resolved | new_player |
| 4 | possible_match | 93,33 | resolved | new_player |
| 5 | homonym (`Ndiaye`) | 100,00 | **pending** | — |
| 6 | possible_match | 93,33 | resolved | new_player |

L'esito `new_player` significa "mantieni identità separate": nessuna riga
storica è stata cancellata, spostata o fusa. I dati statistici restano quindi
identici a quelli di un'importazione da zero. La decisione registrata è
comunque un dato di audit e va trattata come tale.

---

## Fase 14 — Listone ufficiale 2026/2027

**Stato:** completata e verificata il 7 agosto 2026.

- [x] Ricevere il listone.
- [x] Analizzarlo in sola lettura prima di implementare l'import.
- [x] Rilevare fogli, intestazioni, tipi e ID.
- [x] Definire e documentare il mapping specifico.
- [x] Importare ruolo ufficiale separatamente dallo storico.
- [x] Importare squadra ufficiale separatamente dallo storico.
- [x] Importare quotazioni Classic/Mantra e FVM.
- [x] Collegare tramite ID, senza fusioni fuzzy automatiche.
- [x] Predisporre la sostituzione transazionale per aggiornamenti successivi.
- [x] Testare idempotenza.

**Risultato:** 493 calciatori attivi; 427 collegati tramite ID storico; 66
nuovi; 5 ceduti esclusi dallo snapshot corrente. Seconda esecuzione: zero
righe importate (`already_imported`). Backup pre-import salvato in
`database/backups/fantacalcio-pre-listone-20260807.db`.

### Bug/miglioramenti

- Nessuno ancora registrato.

---

## Fase 15 — Documentazione e consegna

**Stato:** non iniziata.

- [ ] Requisiti e installazione.
- [ ] Struttura cartelle.
- [ ] Posizione degli Excel.
- [ ] Configurazione stagioni.
- [ ] Comando di ispezione.
- [ ] Comando di importazione.
- [ ] Avvio backend.
- [ ] Avvio frontend.
- [ ] Esecuzione test.
- [ ] Import listone 2026/2027.
- [ ] Risoluzione mapping.
- [ ] Dizionario dati.
- [ ] Formule delle metriche.
- [ ] Limiti e bias statistici.
- [ ] Verifica completa su Windows.

### Bug/miglioramenti

- Nessuno ancora registrato.

---

## Registro sessioni

### Sessione 2026-07-27 — Primo commit e pubblicazione su GitHub

**Contesto**

Sessione svolta sul PC aziendale con Claude Code, allo scopo di rendere il
progetto recuperabile dal PC di casa.

**Eseguito**

- Verificato che `.gitignore` escludesse Excel, database, report, `.venv`,
  `node_modules` e `.env`, con controllo esplicito della lista dei file da
  versionare.
- Creato il primo commit: 105 file, 19.061 righe.
- Rinominato il branch locale da `master` a `main`.
- Collegato il remoto <https://github.com/JackSammartano/fantastat> e
  pubblicato il branch `main`.
- Rimosso `prompt.txt` dal versionamento su richiesta esplicita, riscrivendo
  il commit; il file resta sul disco locale ed è ora ignorato da Git.
- Riscritto l'autore del commit con l'indirizzo no-reply di GitHub, per non
  esporre pubblicamente l'email aziendale.
- Ispezionato il database reale e rilevata l'anomalia MAP-002.
- Documentata la procedura di migrazione al PC di casa.

**Contenuto effettivamente pubblicato**

Codice backend e frontend, configurazioni, migrazioni, test, documentazione e
`data/manual-mappings/player_mappings.json`.

**Contenuto deliberatamente escluso**

I quattro Excel originali, `database/fantacalcio.db`, `reports/`,
`data/processed/`, `.venv/`, `node_modules/` e i file `.env`. Nessun dato
sensibile e nessuna credenziale risultano pubblicati.

**Stato del database al momento della migrazione**

| Tabella | Righe |
|---|---:|
| players | 1.334 |
| player_aliases | 1.352 |
| seasons | 4 |
| teams | 27 |
| source_imports | 4 |
| source_records | 2.678 |
| player_season_stats | 2.678 |
| player_team_seasons | 2.678 |
| player_mapping_reviews | 6, di cui 5 risolte |
| player_merge_audits | 0 |
| ranking_configs | 0 |
| current_season_list | 0 |

**Problemi aperti**

- MAP-002: le cinque decisioni `new_player` esistono soltanto nel database.
  Rigenerando il database dagli Excel le sei revisioni tornerebbero pendenti.
  I dati statistici non cambierebbero.
- Il diario dichiarava sei revisioni pendenti: affermazione rettificata nella
  fase 13.
- FE-002 resta aperto: l'audit npm è previsto sul PC di casa.

---

### Sessione 2026-07-27 — Fase 10, API core

**Eseguito**

- Installati FastAPI, Uvicorn e HTTPX nell'ambiente locale.
- Creati contratti Pydantic.
- Implementati servizi query giocatore e metriche on demand.
- Implementati filtri, ordinamento e paginazione.
- Implementati dettaglio, storico e confronto.
- Implementate API qualità dati e mapping review.
- Implementata risoluzione transazionale delle revisioni.
- Configurati errori coerenti senza stack trace.
- Configurati CORS e avvio su localhost.
- Verificato OpenAPI.

**File creati**

- `backend/app/schemas/api.py`
- `backend/app/services/player_queries.py`
- `backend/app/api/v1.py`
- `backend/app/main.py`
- `backend/tests/test_api.py`
- `docs/api.md`

**Verifica**

```powershell
.\.venv\Scripts\python.exe -m pytest
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

**Risultato**

- 71 test superati.
- Smoke test reale eseguito senza aprire porte di rete.
- `/health`: 200.
- `/api/v1/seasons`: 4 risultati.
- `/api/v1/players`: 1.334 risultati totali.
- `/api/v1/data-quality/issues`: 7 risultati.
- `/api/v1/player-mappings/pending`: 6 risultati.
- `/openapi.json`: 200.
- Nessun mapping reale modificato durante i test.

**Problemi aperti**

- API-001: warning di deprecazione del TestClient FastAPI/Starlette basato su
  `httpx`; nessun impatto sul runtime.
- Endpoint ranking e importazioni rinviati ai servizi dedicati.

---

### Sessione 2026-07-27 — Fase 9, metriche approvate

**Eseguito**

- Ricevuta approvazione delle sette decisioni.
- Implementate medie semplici e ponderate per `Pv`.
- Implementate ultime stagioni, rapporti e variazioni.
- Implementato decadimento temporale `0,75`.
- Implementate continuità a soglia 19 e volatilità ponderata.
- Implementata affidabilità `50/25/25`.
- Implementate fasce bassa, media e alta.
- Implementato shrinkage opzionale con `K=20`.
- Calcolate le metriche per tutto il database.

**File creati**

- `backend/analytics/__init__.py`
- `backend/analytics/player_metrics.py`
- `backend/scripts/calculate_player_metrics.py`
- `backend/tests/test_player_metrics.py`

**File modificati**

- `docs/scoring-model.md`
- `README.md`
- `DIARIO_PROGETTO.md`

**File generato e ignorato**

- `data/processed/player-metrics.csv`

**Verifica**

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m backend.scripts.calculate_player_metrics
```

**Risultato**

- 63 test superati su 63.
- 1.334 giocatori calcolati.
- Affidabilità alta: 268.
- Affidabilità media: 258.
- Affidabilità bassa: 808.
- 218 giocatori senza fantamedia ponderabile.
- Nessuna modifica alle statistiche persistite.

---

### Sessione 2026-07-27 — Proposta Fase 9, metriche

**Eseguito**

- Analizzate copertura e distribuzioni del database.
- Proposte medie semplici e ponderate per `Pv`.
- Proposte metriche ultime stagioni e rapporti per presenza.
- Proposti cambiamenti assoluti e percentuali.
- Proposto decadimento temporale configurabile.
- Proposte continuità e volatilità.
- Proposti componenti trasparenti dell'affidabilità.
- Proposto, ma non implementato, un punteggio sintetico opzionale.
- Documentato shrinkage opzionale e non predefinito.

**File creati**

- `docs/scoring-model.md`

**File modificati**

- `DIARIO_PROGETTO.md`

**Stato**

- Nessun codice di calcolo implementato.
- Nessuna modifica al database.
- In attesa di approvazione delle sette decisioni elencate nel documento.

---

### Sessione 2026-07-27 — Fase 8, importazione storica

**Eseguito**

- Implementata preparazione preflight del batch.
- Implementata persistenza in transazione unica.
- Implementata idempotenza tramite SHA-256 e vincoli database.
- Persistiti giocatori, alias, stagioni, squadre e statistiche.
- Persistiti record raw e associazioni squadra osservata.
- Persistiti warning e revisioni di matching.
- Creato export CSV elaborato.
- Eseguita due volte l'importazione reale.
- Eseguito audit diretto dei conteggi.
- Testato rollback completo su errore.

**File creati**

- `backend/pipeline/importer.py`
- `backend/scripts/import_seasons.py`
- `backend/tests/test_importer.py`
- `docs/historical-import.md`

**File generati e ignorati**

- `database/fantacalcio.db`
- `data/processed/player-season-stats.csv`
- `reports/import-summary/import-summary.json`

**Prima esecuzione**

```text
status: completed
file importati: 4
righe importate: 2678
giocatori creati: 1334
alias creati: 1352
stagioni create: 4
squadre create: 27
statistiche create: 2678
revisioni create: 6
```

**Seconda esecuzione**

```text
status: already_imported
file saltati: 4
righe importate: 0
nuovi giocatori/statistiche/revisioni: 0
```

**Audit database**

| Tabella | Righe |
|---|---:|
| players | 1.334 |
| player_aliases | 1.352 |
| seasons | 4 |
| teams | 27 |
| source_imports | 4 |
| source_records | 2.678 |
| player_season_stats | 2.678 |
| player_team_seasons | 2.678 |
| player_mapping_reviews | 6 |

**Verifica**

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m backend.scripts.import_seasons
```

**Risultato**

- 56 test superati su 56.
- Idempotenza verificata sul database reale.
- Rollback verificato su database temporaneo.
- CSV elaborato con 2.678 righe.
- Nessun dato inviato in rete.

---

### Sessione 2026-07-27 — Fase 7, validazione

**Eseguito**

- Creato catalogo versionato delle regole.
- Separati errori bloccanti e warning.
- Implementati controlli di intervallo, segno, medie e rigori.
- Implementato controllo duplicati ID-stagione.
- Implementata riconciliazione fra righe sorgente, normalizzate ed escluse.
- Creati report CSV separati e riepilogo JSON.
- Validati tutti i record reali senza persistenza.

**File creati**

- `backend/config/validation_rules.yaml`
- `backend/pipeline/validation.py`
- `backend/scripts/validate_seasons.py`
- `backend/tests/test_validation.py`
- `docs/data-validation.md`

**File generati e ignorati**

- `reports/data-quality/validation/validation-summary.json`
- `reports/data-quality/validation/blocking-errors.csv`
- `reports/data-quality/validation/warnings.csv`
- `reports/data-quality/validation/excluded-rows.csv`

**Verifica**

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m backend.scripts.validate_seasons
```

**Risultato**

- 52 test superati su 52.
- 2.678 righe sorgente.
- 2.678 righe normalizzate.
- Zero righe escluse.
- Zero errori bloccanti.
- Un warning `VAL-ADDITIVE-WITHOUT-PV`.
- Riconciliazione conteggi corretta.
- Database ancora vuoto.

---

### Sessione 2026-07-27 — Fase 6, matching giocatori

**Eseguito**

- Implementato matching certo tramite provider e ID esterno.
- Implementato mapping manuale JSON.
- Raccolti alias, ruoli, squadre e stagioni come contesto.
- Implementati suggerimenti fuzzy con soglia configurabile.
- Impedita qualsiasi fusione automatica basata sul nome.
- Generati report JSON e CSV locali.
- Analizzati tutti i record storici.

**File creati**

- `data/manual-mappings/player_mappings.json`
- `backend/pipeline/matching.py`
- `backend/scripts/analyze_player_matching.py`
- `backend/tests/test_matching.py`
- `docs/player-matching.md`

**File generati e ignorati**

- `reports/unmatched-players/matching-analysis.json`
- `reports/unmatched-players/pending-reviews.csv`

**Verifica**

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m backend.scripts.analyze_player_matching
```

**Risultato**

- 44 test superati su 44.
- 2.678 record analizzati.
- 1.334 identità distinte.
- 1.344 corrispondenze certe dopo la prima occorrenza.
- 18 identità con alias.
- 6 revisioni pendenti.
- Nessuna scrittura nel database.

**Revisioni pendenti**

| Tipo | Sorgente | Candidato |
|---|---|---|
| possible | Milinkovic-Savic | Milinkovic-Savic V. |
| possible | Pellegrini Lo. | Pellegrini Lu. |
| possible | Pavoletti | Paoletti |
| possible | Marin R. | Marin Re. |
| homonym | Ndiaye (ID 7202) | Ndiaye (ID 5859) |
| possible | Braschi | Biraschi |

Tutti i record conservano identità separate finché non viene registrata una
decisione manuale.

---

### Sessione 2026-07-27 — Fase 5, normalizzazione

**Eseguito**

- Implementata normalizzazione pura senza accessi al database.
- Separati valori raw, canonici e analitici.
- Gestiti Unicode NFC, apostrofi, spazi, accenti e `casefold`.
- Creata chiave permissiva per suggerimenti di matching.
- Gestiti numeri italiani, token nulli e percentuali esplicite.
- Validati ruoli Classic e Mantra.
- Applicata la regola `Pv=0` con medie analitiche `null`.
- Conservate statistiche additive anche con `Pv=0`.
- Normalizzati in memoria tutti i record reali.

**File creati**

- `backend/pipeline/normalization.py`
- `backend/tests/test_normalization.py`
- `docs/normalization.md`

**File modificati**

- `README.md`
- `DIARIO_PROGETTO.md`

**Verifica**

```powershell
.\.venv\Scripts\python.exe -m pytest
```

**Risultato**

- 37 test superati su 37.
- 2.678 record reali normalizzati.
- Zero errori di normalizzazione.
- 479 record con medie analitiche correttamente impostate a `null`.
- Nessuna scrittura nel database.
- Nessun remote Git, commit, push o trasferimento di dati.

---

### Sessione 2026-07-27 — Fasi 3 e 4, Git e database

**Eseguito**

- Inizializzato repository Git locale.
- Creato `.venv` con Python 3.12.
- Installato il progetto in modalità editable con dipendenze di sviluppo.
- Aggiunti SQLAlchemy 2 e Alembic.
- Implementate 11 tabelle relazionali.
- Aggiunti vincoli di unicità, integrità referenziale e coerenza statistica.
- Configurato Alembic.
- Generata la migrazione iniziale `d37bd727689e`.
- Creato `database/fantacalcio.db` vuoto.
- Verificata la revisione Alembic head.
- Verificata l'assenza di drift tra modelli e migrazione.
- Verificate le esclusioni Git.

**File principali creati**

- `alembic.ini`
- `backend/app/core/config.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/models/entities.py`
- `backend/migrations/env.py`
- `backend/migrations/script.py.mako`
- `backend/migrations/versions/d37bd727689e_initial_relational_schema.py`
- `backend/tests/test_database_schema.py`
- `database/.gitkeep`
- `docs/database-schema.md`

**File generati e ignorati**

- `.venv/`
- `database/fantacalcio.db`
- `fantacalcio_analysis.egg-info/`

**Verifica**

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\alembic.exe current --check-heads
.\.venv\Scripts\alembic.exe check
git status --short
git check-ignore -v .venv database/fantacalcio.db `
  reports/data-quality/excel-inspection.json `
  Statistiche_Fantacalcio_Stagione_2022_23.xlsx
```

**Risultato**

- 20 test superati su 20.
- Revisione database: `d37bd727689e (head)`.
- Nessun drift Alembic.
- Excel, database, ambiente e report ignorati da Git.
- Nessun commit e nessuna operazione di staging.

**Bug risolto**

- DB-001: transazione implicita del PRAGMA SQLite annullava la registrazione
  della revisione Alembic. Aggiunto commit esplicito prima della migrazione.

---

### Sessione 2026-07-27 — Fase 2, mapping e dizionario dati

**Eseguito**

- Verificati i metadati dei workbook: nessuna fonte incorporata, autore
  `openpyxl`, nessun hyperlink.
- Confrontate le colonne con le pagine statistiche ufficiali Fantacalcio.
- Documentati separatamente riscontri ufficiali, relazioni nei dati e conferme
  dell'utente.
- Creato il mapping versionato delle 18 colonne.
- Implementato il caricamento e la validazione del mapping.
- Aggiunti controlli per colonne mancanti, inattese, duplicate e fuori ordine.
- Aggiunti controlli per nomi canonici duplicati e colonne peso inesistenti.
- Verificato il mapping sulle intestazioni reali di tutte e quattro le stagioni.

**File creati**

- `backend/config/column_mapping.yaml`
- `backend/pipeline/__init__.py`
- `backend/pipeline/column_mapping.py`
- `backend/tests/test_column_mapping.py`
- `docs/data-dictionary.md`

**File modificati**

- `README.md`
- `DIARIO_PROGETTO.md`

**Verifica**

```powershell
python -m pytest
```

**Risultato**

- 13 test superati su 13.
- Tutte le quattro intestazioni reali risultano valide, complete, univoche e
  nello stesso ordine del mapping.
- Nessun database creato.
- Git non inizializzato.
- Excel originali non modificati.

**Problemi aperti**

- I workbook non dichiarano direttamente la propria fonte.
- `R-` è semanticamente supportato dalla relazione verificata
  `Rc = R+ + R-`; il dizionario conserva esplicitamente questo livello di
  evidenza.

---

### Sessione 2026-07-27 — Fase 1, ispettore ripetibile

**Eseguito**

- Creata la struttura minima della fase 1.
- Configurate le quattro stagioni tramite percorsi relativi.
- Implementato l'ispettore read-only.
- Implementati report deterministici JSON e Markdown.
- Aggiunti quattro test sintetici.
- Installato `pytest 8.4.2` su autorizzazione esplicita.
- Eseguiti con successo tutti i test.
- Analizzati con successo i quattro workbook reali.
- Confermati tutti i conteggi dell'analisi iniziale.

**File creati o modificati**

- `.gitignore`
- `pyproject.toml`
- `README.md`
- `backend/__init__.py`
- `backend/config/seasons.yaml`
- `backend/scripts/__init__.py`
- `backend/scripts/inspect_excel.py`
- `backend/tests/__init__.py`
- `backend/tests/test_inspect_excel.py`
- `backend/tests/fixtures/.gitkeep`
- `docs/import-process.md`
- `reports/.gitkeep`
- `DIARIO_PROGETTO.md`

**File generati**

- `reports/data-quality/excel-inspection.json`
- `reports/data-quality/excel-inspection.md`

**Verifica**

```powershell
python -m pytest
python -m backend.scripts.inspect_excel
```

**Risultato**

- Test: 4 superati su 4.
- Workbook: 4 analizzati.
- File originali: non modificati.
- Database e Git: non inizializzati.

**Problemi aperti**

- Significato ufficiale delle abbreviazioni ancora da confermare.
- Aggiungere in futuro il confronto completo delle righe tra fogli.

---

### Sessione 2026-07-27 — Analisi iniziale

**Eseguito**

- Ispezionata la root.
- Analizzati in memoria i quattro workbook.
- Confrontati fogli, colonne, tipi e conteggi.
- Verificati ID, nomi, ruoli, squadre, duplicati, null e anomalie.
- Proposti architettura, schema dati, API e piano.
- Ricevuta approvazione generale.
- Confermato che `Squadra` è soltanto un valore sorgente.
- Creato questo diario.

**File creati**

- `DIARIO_PROGETTO.md`

**File modificati**

- Nessuno.

**Verifica**

- Aprire `DIARIO_PROGETTO.md`.
- Controllare la sezione **Stato corrente**.
- Controllare che la **Prossima azione esatta** corrisponda al punto di ripresa
  desiderato.

**Problemi aperti**

- Manca il dizionario ufficiale delle abbreviazioni.
- Git e database sono intenzionalmente rinviati al PC di casa.

---

### Sessione 2026-07-27 — Fase 11, frontend base

**Eseguito**

- Creato frontend React 19, TypeScript e Vite, eseguito soltanto in locale.
- Implementati layout responsivo, dashboard, elenco filtrabile e paginato,
  dettaglio giocatore e grafici Recharts.
- Aggiunti indicatore di affidabilità ed export CSV della pagina corrente.
- Aggiunti test frontend e configurazione Vitest.
- Rimossi font remoti: l'interfaccia usa i font di sistema.

**File creati o modificati**

- `frontend/package.json` e `frontend/package-lock.json`
- configurazioni TypeScript, Vite ed ESLint sotto `frontend/`
- `frontend/src/api/client.ts`
- `frontend/src/models/api.ts`
- `frontend/src/components/*`
- `frontend/src/pages/*`
- `frontend/src/styles.css`
- test frontend sotto `frontend/src/`
- `DIARIO_PROGETTO.md`

**Verifica**

```powershell
cd frontend
npm run lint
npm test
npm run build
cd ..
.\.venv\Scripts\python.exe -m pytest
```

**Risultato**

- ESLint: superato.
- Frontend: 3 test superati.
- Build Vite: completata.
- Backend: 71 test superati, un warning di deprecazione già registrato.
- Excel originali non modificati; nessun commit, push o deploy eseguito.

**Problemi aperti**

- Bundle JavaScript iniziale sopra 500 kB: ottimizzare con caricamento lazy.
- `npm install` aveva segnalato vulnerabilità nelle dipendenze; eseguire un
  audit controllato a casa prima di qualunque aggiornamento, evitando
  correzioni forzate non verificate.

**Completamento successivo della fase**

- Aggiunto filtro testuale esatto per la squadra tramite il parametro API
  verificato `team`.
- Aggiunto selettore di visibilità per tutte le colonne della tabella.
- Aggiunti azzeramento filtri e stato dedicato senza risultati.
- Aggiunto test del client API per tutti i filtri principali.
- Verifica finale: ESLint superato, 4 test frontend superati e build completata.

---

### Sessione 2026-07-27 — Trend giocatori e metriche portieri

**Eseguito**

- Aggiunte tendenze storiche di media voto e fantamedia nel dettaglio
  giocatore, calcolate su tutte le stagioni disponibili.
- Usata regressione lineare ponderata per partite a voto, senza soglie
  qualitative nascoste.
- Aggiunti gol subiti per presenza e rigori parati per presenza.
- Limitate le nuove metriche al ruolo portiere nel ranking.
- Aggiornate documentazione e interfaccia.

**Verifica**

- 83 test backend superati.
- 8 test frontend superati.
- ESLint e build Vite superati.
- Formula documentata in `docs/scoring-model.md`.

---

## Registro generale bug

| ID | Fase | Descrizione | Gravità | Stato | Risoluzione |
|---|---|---|---|---|---|
| DQ-001 | Analisi | Lazetic: `Pv=0`, `Amm=1` | warning | aperto | conservare e segnalare |
| DQ-002 | Analisi | `Mv/Fm=0` usati come sentinella con `Pv=0` | medio | deciso | normalizzare a `null`, conservare raw |
| DQ-003 | Matching | `Ndiaye` associato a due ID | alto | aperto | non unire automaticamente |
| DB-001 | Database | Alembic non registrava la revisione dopo il PRAGMA | alto | risolto | commit del PRAGMA prima della migrazione |
| API-001 | Test API | TestClient segnala futura deprecazione di `httpx` | basso | aperto | migrare quando il nuovo client sarà stabile |
| FE-001 | Build frontend | Bundle iniziale superiore a 500 kB | basso | risolto | lazy loading: bundle iniziale circa 235 kB |
| FE-002 | Dipendenze | `npm install` segnala 7 vulnerabilità high | medio | aperto | audit controllato sul PC di casa |
| MAP-001 | Mapping | La conferma registra audit ma non fonde lo storico importato | alto | risolto | anteprima, transazione, backup e rollback |
| MAP-002 | Mapping | Le decisioni `new_player` restano solo nel database e non nel mapping versionato | medio | aperto | trasferire il database, oppure estendere la sincronizzazione a tutti gli esiti |
| GIT-001 | Git | Il primo commit era firmato con l'email aziendale | basso | risolto | commit riscritto con l'indirizzo no-reply GitHub |

## Registro generale miglioramenti

| ID | Fase | Miglioramento | Priorità | Stato |
|---|---|---|---|---|
| IMP-001 | Ispezione | Report Markdown e JSON deterministico | alta | pianificato |
| IMP-002 | Ispezione | SHA-256 dei file sorgente | alta | pianificato |
| IMP-003 | Matching | Alias derivati dagli ID stabili | alta | pianificato |
| IMP-004 | Qualità | Distinguere raw, normalized e analytical | alta | pianificato |
| IMP-005 | Ranking | Mostrare composizione del punteggio | alta | pianificato |
| IMP-006 | Mapping | Mapping separato per futuri formati differenti | alta | pianificato |
| IMP-007 | Frontend | Filtro squadra, selezione colonne e empty state | media | completato |
| IMP-008 | Mapping | Sincronizzare decisioni DB nel mapping manuale | alta | parziale, si veda MAP-002 |
