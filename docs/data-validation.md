# Validazione e report di qualità

## Obiettivo

La validazione opera dopo mapping e normalizzazione, ma prima di qualsiasi
scrittura nel database. Nessuna anomalia viene ignorata silenziosamente.

## Regole bloccanti

- ID duplicato nella stessa stagione;
- `Pv` negativo o superiore a 38;
- media voto fuori dall'intervallo 0–10;
- media mancante quando `Pv>0`;
- media valorizzata quando `Pv=0`;
- statistica additiva negativa;
- `rigori calciati != rigori segnati + rigori sbagliati`;
- errore di mapping, conversione o normalizzazione.

Il limite 38 deriva dal numero di giornate delle stagioni analizzate ed è
configurato in `backend/config/validation_rules.yaml`.

Non è imposto un limite arbitrario alla fantamedia: bonus e malus possono
portarla fuori dall'intervallo del voto puro.

## Warning

- statistiche additive non nulle con `Pv=0`;
- gol superiori alle partite a voto;
- assist superiori alle partite a voto.

Gol e assist superiori a `Pv` non sono necessariamente impossibili, quindi non
causano esclusione.

## Report

```powershell
python -m backend.scripts.validate_seasons
```

Genera in `reports/data-quality/validation/`:

- `validation-summary.json`;
- `blocking-errors.csv`;
- `warnings.csv`;
- `excluded-rows.csv`.

Il comando termina con codice diverso da zero in presenza di errori bloccanti o
righe escluse, così potrà essere utilizzato in una pipeline automatica.

