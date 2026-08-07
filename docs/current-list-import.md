# Importazione listone ufficiale 2026/2027

## Sorgente e mapping

Il file configurato è `Quotazioni_Fantacalcio_Stagione_2026_27.xlsx` e viene
sempre aperto in sola lettura. Il foglio canonico è `Tutti`; `Portieri`,
`Difensori`, `Centrocampisti` e `Attaccanti` devono contenere esattamente gli
stessi ID del rispettivo ruolo. `Ceduti` è escluso dallo stato corrente e il
suo conteggio resta nel report.

| Colonna | Campo analitico |
|---|---|
| `Id` | ID esterno Fantacalcio |
| `R`, `RM` | ruolo ufficiale Classic e ruoli Mantra |
| `Nome`, `Squadra` | nome e squadra ufficiali correnti |
| `Qt.A`, `Qt.I` | quotazione Classic attuale e iniziale |
| `Qt.A M`, `Qt.I M` | quotazione Mantra attuale e iniziale |
| `FVM`, `FVM M` | FVM Classic e Mantra |

`Diff.` e `Diff.M` sono validati rispettivamente contro `Qt.A - Qt.I` e
`Qt.A M - Qt.I M`, ma non vengono duplicati nel database perché derivabili.

## Identità e aggiornamenti

- un ID esterno già presente collega il record al calciatore storico;
- un ID mai visto crea un calciatore con stato `new_player`;
- nomi simili non producono fusioni automatiche;
- ogni sorgente resta in `source_imports` e `source_records` con SHA-256;
- una nuova versione del file sostituisce transazionalmente lo snapshot in
  `current_season_list`, conservando i record sorgente precedenti per audit;
- lo stesso SHA-256 viene ignorato come già importato.

## Comando e report

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.import_current_list
```

Il riepilogo JSON viene scritto in
`reports/current-list-import/import-summary.json`.
