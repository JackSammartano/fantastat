# Dizionario dati delle stagioni storiche

## Ambito e provenienza

Il dizionario descrive le intestazioni effettivamente presenti nei quattro
workbook dal 2022/2023 al 2025/2026.

I file non contengono URL o metadati utili a identificarne la fonte: il campo
`creator` vale `openpyxl`. La struttura coincide però con quella pubblicata
dalla pagina ufficiale delle statistiche Fantacalcio:

- <https://www.fantacalcio.it/statistiche-serie-a/2025-26/italia/riepilogo>
- <https://www.fantacalcio.it/comparatore>

La pagina ufficiale descrive il database come consultabile per partite giocate,
media voto, media Fantavoto, gol, assist, gol subiti, ammonizioni, espulsioni,
rigori segnati/tirati e rigori parati. Le pagine dei singoli portieri espongono
inoltre partite a voto, gol subiti, assist, ammonizioni, rigori parati,
espulsioni e autoreti.

Lo stato semantico di ogni campo è conservato anche nella configurazione
`backend/config/column_mapping.yaml`.

## Stati semantici

| Stato | Significato |
|---|---|
| `verified_official` | significato riscontrato su una pagina ufficiale |
| `verified_from_data` | significato o comportamento verificato nei file |
| `verified_official_and_data_relation` | riscontro ufficiale e relazione interna verificata |
| `verified_from_data_relation` | interpretazione supportata da una relazione valida su tutti i record |
| `user_confirmed` | semantica dichiarata esplicitamente dall'utente |

## Campi

| Sorgente | Canonico | Tipo analitico | Null | Significato | Aggregazione prevista |
|---|---|---|---|---|---|
| `Id` | `external_player_id` | intero | no | identificativo esterno | nessuna |
| `R` | `classic_role` | stringa | no | ruolo Classic storico | nessuna |
| `Rm` | `mantra_roles` | stringa | no | ruolo/i Mantra storici | nessuna |
| `Nome` | `source_player_name` | stringa | no | nome visualizzato sorgente | nessuna |
| `Squadra` | `source_team_name` | stringa | no | semplice valore sorgente | nessuna |
| `Pv` | `rated_appearances` | intero | no | partite/presenze a voto | somma solo per record disgiunti |
| `Mv` | `average_rating` | decimale | sì | media voto | media ponderata su `Pv` |
| `Fm` | `fantasy_average` | decimale | sì | media Fantavoto/fantamedia | media ponderata su `Pv` |
| `Gf` | `goals_scored` | intero | no | gol segnati | somma solo per record disgiunti |
| `Gs` | `goals_conceded` | intero | no | gol subiti | somma solo per record disgiunti |
| `Rp` | `penalties_saved` | intero | no | rigori parati | somma solo per record disgiunti |
| `Rc` | `penalties_taken` | intero | no | rigori calciati/tirati | somma solo per record disgiunti |
| `R+` | `penalties_scored` | intero | no | rigori segnati | somma solo per record disgiunti |
| `R-` | `penalties_missed` | intero | no | rigori non segnati | somma solo per record disgiunti |
| `Ass` | `assists` | intero | no | assist | somma solo per record disgiunti |
| `Amm` | `yellow_cards` | intero | no | ammonizioni | somma solo per record disgiunti |
| `Esp` | `red_cards` | intero | no | espulsioni | somma solo per record disgiunti |
| `Au` | `own_goals` | intero | no | autoreti/autogol | somma solo per record disgiunti |

## Regole verificate

- `Rc = R+ + R-` su tutti i 2.678 record.
- Se `Pv > 0`, `Mv` e `Fm` sono diverse da zero.
- Se `Pv = 0`, `Mv` e `Fm` sorgente valgono zero.
- In analisi, `Mv` e `Fm` diventano `null` quando `Pv = 0`.
- Gli zeri delle statistiche additive rimangono zeri.
- Un giocatore assente dalla stagione non riceve un record artificiale a zero.
- `Squadra` non riceve una semantica temporale aggiuntiva.

## Aggregazione

`sum_if_disjoint` non autorizza automaticamente una somma. Significa che il
campo è additivo soltanto quando sia stato prima dimostrato che i record
rappresentano insiemi disgiunti. Nei quattro workbook attuali ogni ID compare
una sola volta per stagione, quindi non è necessaria alcuna aggregazione.

Le medie non devono mai essere sommate. Se in futuro saranno presenti record
disgiunti compatibili, la formula candidata è:

```text
media_ponderata = somma(media_record × Pv_record) / somma(Pv_record)
```

La formula sarà applicabile solo se `Pv` è coerente con il numero di voti usato
per calcolare entrambe le medie.

## Campi non disponibili

I workbook attuali non contengono:

- minuti;
- titolarità;
- ingressi;
- presenze senza voto;
- clean sheet;
- infortuni;
- quotazioni;
- data di nascita;
- identificativi di squadra.

Questi valori non devono essere inventati o derivati senza una nuova sorgente.

