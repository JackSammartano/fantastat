# Proposta metriche storiche e affidabilità

> Stato: **approvato e implementato il 27 luglio 2026**.

## Evidenze del dataset

| Indicatore | Valore |
|---|---:|
| giocatori | 1.334 |
| record giocatore-stagione | 2.678 |
| giocatori con 1 stagione | 592 |
| giocatori con 2 stagioni | 337 |
| giocatori con 3 stagioni | 208 |
| giocatori con 4 stagioni | 197 |
| record con `Pv=0` | 479 |
| mediana `Pv` per stagione | 16 |
| 75° percentile `Pv` per stagione | 28 |
| mediana `Pv` complessive per giocatore | 20 |
| 75° percentile `Pv` complessive | 52,75 |

La qualità del campione deve quindi essere mostrata separatamente dal
rendimento.

## Convenzioni

- Una stagione assente non entra nelle medie e non diventa uno zero.
- Una stagione presente con `Pv=0` conserva le statistiche additive, ma non
  entra nelle medie di `Mv` e `Fm`.
- `Pv` è l'unico peso disponibile nei file attuali.
- Non esistono minuti o un conteggio voti distinto da `Pv`.
- Le metriche vengono calcolate soltanto sulle stagioni selezionate dall'utente.

## Metriche descrittive proposte

### Media semplice delle stagioni

```text
media_semplice = somma(media_stagionale non null) / stagioni con media
```

Da mostrare per `Mv` e `Fm`, sempre insieme al numero di stagioni considerate.

### Media ponderata per partite a voto

```text
media_ponderata_Pv =
    somma(media_stagionale × Pv_stagione) / somma(Pv_stagione)
```

Se la somma di `Pv` è zero, il risultato è `null`.

Questa non verrà chiamata “ponderata sui voti validi” finché non esisterà una
colonna distinta che lo dimostri.

### Ultima stagione e ultime due stagioni

- `latest`: dato dell'ultima stagione disponibile nel periodo selezionato;
- `latest_two_simple`: media semplice delle ultime due stagioni con dato;
- `latest_two_weighted`: media ponderata per `Pv` delle ultime due stagioni.

“Ultima disponibile” e “ultima stagione di calendario” saranno campi distinti:
un giocatore assente nell'ultima stagione non deve sembrare attivo.

### Rapporti per presenza

Calcolabili soltanto quando `Pv>0`:

```text
goals_per_appearance   = gol / Pv
assists_per_appearance = assist / Pv
bonus_events_per_appearance = (gol + assist + rigori_parati) / Pv
malus_events_per_appearance =
    (ammonizioni + espulsioni + autogol + rigori_sbagliati + gol_subiti) / Pv
```

`bonus_events` e `malus_events` sono conteggi di eventi, non punti
Fantacalcio: non applicano pesi regolamentari arbitrari.

### Rapporto fantamedia/media voto

```text
fm_mv_delta = Fm - Mv
fm_mv_ratio = Fm / Mv, soltanto se Mv != 0
```

Si propone `delta` come visualizzazione principale perché il rapporto può
amplificare differenze su denominatori piccoli.

### Variazione recente

```text
absolute_change = latest - previous
percentage_change = (latest - previous) / abs(previous) × 100
```

La percentuale è `null` se uno dei dati manca o se `previous=0`.

## Recency weighting — decisione richiesta

Proposta: decadimento geometrico configurabile.

```text
recency_weight(age) = decay ^ age

media_recente =
    somma(media × Pv × recency_weight) /
    somma(Pv × recency_weight)
```

Dove `age=0` per la stagione più recente.

Valore iniziale proposto:

```text
decay = 0,75
```

Con quattro stagioni, dalla più recente alla più vecchia:

```text
1,0000 — 0,7500 — 0,5625 — 0,4219
```

Il parametro resterà modificabile. Alternative:

- `1,00`: nessuna preferenza temporale;
- `0,50`: forte preferenza per il dato recente.

## Continuità

Non propongo una soglia nascosta. La metrica sarà parametrica:

```text
continuity(threshold) =
    stagioni con Pv >= threshold / stagioni selezionate
```

In questa metrica specifica, una stagione assente conta come mancato
raggiungimento della soglia, ma non viene trasformata in un record statistico a
zero.

Valore iniziale proposto:

```text
threshold = 19
```

Motivo: metà delle 38 giornate. L'utente potrà scegliere un'altra soglia.

## Volatilità

Per giocatori con almeno due stagioni aventi `Pv>0`:

```text
media = media ponderata per Pv

varianza_ponderata =
    somma(Pv × (media_stagionale - media)^2) / somma(Pv)

volatilità = radice_quadrata(varianza_ponderata)
```

Con meno di due stagioni valide il risultato è `null`, non zero.

## Tendenza su tutte le stagioni

Media voto e fantamedia espongono una pendenza tramite regressione lineare
ponderata per `Pv`:

```text
peso = Pv della stagione
x = posizione cronologica della stagione selezionata
y = Mv oppure Fm
trend_slope = covarianza_ponderata(x, y) / varianza_ponderata(x)
```

- valore positivo: crescita storica media per stagione;
- valore negativo: calo storico medio per stagione;
- con meno di due stagioni valide: `null`.

La pendenza descrive i dati disponibili e non rappresenta una previsione.

## Metriche specifiche dei portieri

```text
goals_conceded_per_appearance = gol_subiti / Pv
penalties_saved_per_appearance = rigori_parati / Pv
```

Sono `null` quando `Pv=0`. Nel ranking la prima è `lower is better`, la seconda
è `higher is better`; entrambe sono selezionabili soltanto per il ruolo `P`.

## Affidabilità del campione

### Componenti sempre visibili

Propongo di mostrare sempre:

- `total_pv`;
- `available_seasons`;
- `selected_seasons`;
- `latest_calendar_season_pv`;
- `seasons_with_pv`;
- eventuali warning di qualità;
- mapping certo, manuale o pendente.

Questi dati sono più trasparenti di un singolo voto.

### Punteggio sintetico opzionale — decisione richiesta

Proposta iniziale:

```text
sample_component   = min(total_pv / 76, 1)
coverage_component = available_seasons / selected_seasons
recent_component   = min(latest_calendar_season_pv / 19, 1)

reliability_score =
    100 × (
        0,50 × sample_component +
        0,25 × coverage_component +
        0,25 × recent_component
    )
```

Motivazioni:

- 76 presenze equivalgono a due stagioni complete;
- 19 presenze equivalgono a metà dell'ultima stagione;
- la dimensione totale del campione pesa più delle altre componenti.

Penalità trasparenti proposte:

- mapping pendente: il punteggio resta calcolato, ma viene mostrato un badge;
- warning qualità: badge separato, nessuna penalità numerica automatica;
- meno di due stagioni valide: volatilità non disponibile.

Non propongo di ridurre direttamente `Fm` o `Mv`: affidabilità e rendimento
devono restare due dimensioni separate.

### Fasce visuali opzionali

Se approvato il punteggio:

```text
0–39   bassa
40–69  media
70–100 alta
```

Le fasce hanno solo funzione di interfaccia e non modificano ranking o medie.

## Small-sample shrinkage — non consigliato come default

Per una classifica avanzata si potrebbe avvicinare la fantamedia dei piccoli
campioni alla media del ruolo:

```text
weight = total_pv / (total_pv + K)
adjusted_fm = weight × player_fm + (1-weight) × role_mean_fm
```

Con proposta `K=20`, pari alla mediana delle presenze complessive osservate.

Questa metrica è utile ma introduce una scelta modellistica forte. Propongo di:

- non usarla nelle statistiche principali;
- renderla opzionale nei ranking;
- mostrarne sempre valore grezzo, valore corretto e peso applicato.

## Decisioni approvate

1. Metriche descrittive e formule per presenza approvate.
2. `decay=0,75` approvato come default modificabile.
3. `threshold=19` approvato per la continuità.
4. Punteggio sintetico di affidabilità approvato.
5. Pesi `50% / 25% / 25%` approvati.
6. Fasce bassa/media/alta approvate.
7. Shrinkage opzionale con `K=20` approvato.

## Implementazione

```text
backend/analytics/player_metrics.py
backend/scripts/calculate_player_metrics.py
backend/tests/test_player_metrics.py
```

Comando:

```powershell
python -m backend.scripts.calculate_player_metrics
```

Output:

```text
data/processed/player-metrics.csv
```

Il calcolo non modifica le statistiche storiche nel database.

## Risultato iniziale

- giocatori calcolati: 1.334;
- affidabilità alta: 268;
- affidabilità media: 258;
- affidabilità bassa: 808;
- giocatori senza fantamedia ponderabile: 218.
