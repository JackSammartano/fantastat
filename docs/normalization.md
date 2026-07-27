# Regole di normalizzazione

La normalizzazione è una trasformazione pura: non modifica gli Excel e non
scrive nel database.

## Livelli conservati

Ogni record mantiene tre rappresentazioni:

1. `raw`: colonne e valori originali;
2. `canonical_source`: colonne rinominate, valori ancora originali;
3. `analytical`: valori puliti e pronti per validazione e persistenza.

## Testi e nomi

- Unicode normalizzato in NFC;
- spazi iniziali/finali rimossi;
- spazi multipli ridotti;
- apostrofi tipografici convertiti in `'`;
- display con accenti conservati;
- forma normalizzata tramite `casefold`;
- chiave di confronto senza accenti e punteggiatura.

La chiave permissiva serve soltanto a cercare candidati. Non autorizza una
fusione automatica.

## Squadre

Per ora si applica soltanto normalizzazione meccanica. Non esiste una tabella di
alias inventata: `Squadra` resta un valore sorgente.

## Numeri

Sono supportati:

- numeri Python;
- virgola decimale italiana;
- punto delle migliaia quando è presente la virgola;
- token nulli `-`, `N.D.`, `n/a`, stringa vuota;
- percentuali soltanto quando richieste esplicitamente.

Le conversioni usano `Decimal`, evitando passaggi intermedi in `float`.

## Zeri e assenze

- con `Pv=0`, `Mv` e `Fm` analitiche diventano `null`;
- gli zeri originali restano in `raw` e `canonical_source`;
- statistiche additive, come l'ammonizione di Lazetic, restano valorizzate;
- una stagione mancante non genera alcun record artificiale.

