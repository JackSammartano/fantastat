# API REST locale

## Avvio sicuro in locale

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

L'host `127.0.0.1` rende il servizio raggiungibile soltanto dal computer locale.

Documentazione interattiva:

- <http://127.0.0.1:8000/docs>
- <http://127.0.0.1:8000/openapi.json>

## Endpoint implementati

### Listone corrente

`GET /api/v1/current-list` espone lo snapshot ufficiale 2026/2027 con
paginazione, ricerca, filtri per ruolo, squadra, stato identità e intervallo di
quotazione. Supporta ordinamento per nome, squadra, quotazioni e FVM Classic o
Mantra. Ogni riga include `player_id` per aprire lo storico del calciatore e il
numero di stagioni storiche disponibili.

`GET /api/v1/players/{id}` include anche `current_list`, con squadra, ruoli,
quotazioni e FVM ufficiali. Il valore è `null` per un'identità non presente nel
listone corrente.

```text
GET  /health
GET  /api/v1/seasons
GET  /api/v1/players
GET  /api/v1/players/{id}
GET  /api/v1/players/{id}/history
GET  /api/v1/players/compare?ids=1&ids=2
GET  /api/v1/rankings
POST /api/v1/rankings/calculate
GET  /api/v1/ranking-configs
POST /api/v1/ranking-configs
PUT  /api/v1/ranking-configs/{id}
DELETE /api/v1/ranking-configs/{id}
GET  /api/v1/data-quality/issues
GET  /api/v1/player-mappings/pending
POST /api/v1/player-mappings/{id}/resolve
GET  /api/v1/player-mappings/{id}/merge-preview
POST /api/v1/player-mappings/{id}/merge
POST /api/v1/player-merges/{audit_id}/revert
```

## Elenco giocatori

Parametri:

- `search`;
- `role=P|D|C|A`;
- `team`;
- `min_appearances`;
- `min_seasons`;
- `page`;
- `page_size`, massimo 100;
- `sort_by`;
- `sort_order`.

La risposta include paginazione e affidabilità calcolata.

## Errori

Gli errori applicativi hanno forma:

```json
{
  "error": "http_error",
  "detail": "Giocatore non trovato"
}
```

Gli errori imprevisti non espongono stack trace.

## Risoluzione mapping

Risoluzioni accettate:

- `confirm_candidate`;
- `new_player`;
- `exclude`.

Una revisione già risolta restituisce HTTP 409.

La fusione richiede prima un'anteprima. Il token dell'anteprima lega
l'applicazione allo stato verificato; conflitti di stagione o alias bloccano
l'operazione. Prima della transazione viene creato un backup SQLite locale e
la fusione può essere annullata tramite il relativo audit.

## Ranking

`GET /api/v1/rankings` espone metriche ammesse e relativa direzione.

`POST /api/v1/rankings/calculate` richiede ruolo, stagioni, soglia presenze,
decadimento temporale, soglia di continuità e pesi espliciti. La risposta
include valori originali, percentili, pesi e contributi.

Le configurazioni sono salvabili nel database locale tramite
`/api/v1/ranking-configs`. Non vengono applicati preset impliciti.

## Endpoint rinviati intenzionalmente

- trigger HTTP delle importazioni.

Saranno aggiunti insieme ai rispettivi servizi applicativi e alle relative
protezioni, evitando di esporre operazioni incomplete.
