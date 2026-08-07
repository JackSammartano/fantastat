# Proposta calcolo ranking configurabile

> Stato: **approvato e implementato il 27 luglio 2026**.

## Principi

- Il ruolo è obbligatorio e il confronto avviene soltanto tra i calciatori del
  listone corrente che hanno quel ruolo ufficiale 2026/2027.
- L'utente sceglie stagioni, minimo di presenze e pesi.
- La stagione corrente senza statistiche non entra nelle metriche, nella
  copertura o nell'affidabilità: il rendimento usa soltanto lo storico.
- Le metriche storiche utilizzano le formule già approvate.
- Affidabilità e rendimento restano separati. L'affidabilità entra nel
  punteggio soltanto se l'utente le assegna esplicitamente un peso.
- Il risultato mostra sempre la composizione del punteggio.

## Metriche iniziali selezionabili

- `fantasy_average_recency_weighted` — maggiore è meglio;
- `average_rating_recency_weighted` — maggiore è meglio;
- `goals_per_appearance` — maggiore è meglio;
- `goals_conceded_per_appearance` — minore è meglio, solo portieri;
- `penalties_saved_per_appearance` — maggiore è meglio, solo portieri;
- `assists_per_appearance` — maggiore è meglio;
- `bonus_events_per_appearance` — maggiore è meglio;
- `malus_events_per_appearance` — minore è meglio;
- `continuity` — maggiore è meglio;
- `fantasy_average_volatility` — minore è meglio;
- `latest_fantasy_average` — maggiore è meglio;
- `fantasy_average_trend_slope` — maggiore è meglio; pendenza della regressione
  storica ponderata per presenze;
- `reliability_score` — maggiore è meglio, opzionale.

La tabella mostra inoltre pendenza, variazione fra le ultime due stagioni,
percentile del trend nel ruolo, stagioni valide e presenze. Il trend resta una
descrizione dello storico e non viene presentato come previsione.

## Normalizzazione proposta

Ogni metrica viene trasformata in rango percentile `0–100` all'interno del
pool filtrato per ruolo, stagioni e presenze:

```text
percentile = posizione_relativa_nel_pool × 100
```

Per le metriche in cui un valore inferiore è migliore, l'ordinamento è
invertito. I valori uguali ricevono il percentile medio delle posizioni
occupate.

Motivo della scelta: metriche con unità diverse diventano confrontabili senza
attribuire soglie assolute arbitrarie. Il punteggio resta però relativo al pool
selezionato: modificando filtri o stagioni possono cambiare anche i percentili.

## Punteggio

I pesi sono numeri non negativi e almeno uno deve essere maggiore di zero:

```text
score =
    somma(percentile_metrica × peso_metrica) /
    somma(pesi)
```

Il punteggio finale è compreso tra `0` e `100`.

## Valori mancanti

Proposta conservativa:

- un giocatore privo di una metrica con peso maggiore di zero viene escluso
  dalla classifica;
- l'esclusione viene conteggiata e motivata nella risposta;
- non si trasformano i valori mancanti in zero;
- togliendo il peso alla metrica, questa non costituisce più causa di
  esclusione.

## Parametri della richiesta

```text
role
selected_seasons[]
minimum_appearances
recency_decay
continuity_threshold
metric_weights{}
```

La risposta conterrà:

```text
configurazione applicata
dimensione del pool iniziale
giocatori esclusi e motivazioni
posizione
player_id e nome
score finale
valore originale, percentile, peso e contributo per ogni metrica
affidabilità e numero di presenze
```

## Decisioni richieste

1. Approvare il percentile nel pool come normalizzazione.
2. Approvare l'esclusione quando manca una metrica pesata.
3. Approvare l'elenco iniziale delle metriche e la loro direzione.
4. Decidere se fornire preset iniziali per ruolo oppure partire sempre con pesi
   impostati manualmente.

## Preset didattici dell'interfaccia

L'interfaccia fornisce quattro configurazioni modificabili, una per ruolo:
portiere equilibrato, difensore da bonus, centrocampista offensivo e attaccante
da bonus. Servono a rendere comprensibile il meccanismo dei pesi e non sono
presentate come valutazioni oggettive o previsioni.
