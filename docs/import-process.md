# Processo di importazione

## Stato attuale

È implementata soltanto la fase di ispezione. Lo script non scrive nel database,
non normalizza i dati e non modifica i workbook.

## Principi

1. Gli Excel originali sono sorgenti in sola lettura.
2. Il foglio `Tutti` è la sorgente canonica.
3. I fogli per ruolo servono come controllo di coerenza.
4. Ogni file è identificato anche tramite SHA-256.
5. Valori originali, normalizzati e analitici resteranno distinti.
6. L'assenza da una stagione non sarà convertita in zero.
7. Il campo `Squadra` sarà conservato come semplice valore sorgente.
8. Matching ambiguo e omonimi richiederanno revisione manuale.

## Ispezione

Il comando:

```powershell
python -m backend.scripts.inspect_excel
```

controlla:

- presenza dei file e dei fogli configurati;
- dimensioni e intestazioni;
- tipi rilevati;
- formule e celle unite;
- colonne vuote e valori mancanti;
- righe e ID duplicati;
- coerenza dei fogli per ruolo con `Tutti`;
- intervalli numerici e valori negativi;
- giocatori con zero presenze valide ma statistiche non nulle;
- stabilità di ID, nomi e ruoli tra stagioni;
- omonimi associati a ID differenti.

## Fasi successive

Mapping, normalizzazione, matching, validazione, salvataggio SQLite ed export
saranno implementati soltanto dopo la verifica del report di ispezione.

