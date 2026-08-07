# Pubblicazione GitHub Pages

La versione Pages è uno snapshot pubblico e di sola consultazione. Non include
Excel, database SQLite, report, backup o funzioni amministrative.

## Aggiornare i dati pubblici

Con database locale aggiornato:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.export_static_site
cd frontend
$env:VITE_STATIC_MODE="true"
npm run build
Remove-Item Env:\VITE_STATIC_MODE
cd ..
```

Lo snapshot generato è `frontend/public/data/snapshot.json`. Contiene soltanto
i 493 giocatori del listone corrente, storico e metriche necessarie.

## Funzioni disponibili

- dashboard, listone, filtri e schede;
- grafici e confronto;
- ranking e trend calcolati interamente nel browser;
- configurazioni ranking salvate nel `localStorage` del singolo dispositivo.

Revisioni mapping e altre scritture non sono pubblicate. Il routing usa hash
URL per essere compatibile con GitHub Pages sotto `/fantastat/`.

## Deploy

Il workflow `.github/workflows/pages.yml` esegue test, lint, build e deploy a
ogni push su `main`. Nelle impostazioni GitHub del repository, Pages deve usare
`GitHub Actions` come sorgente.
