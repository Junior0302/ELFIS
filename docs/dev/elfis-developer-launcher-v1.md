# ELFIS Developer Launcher V1

Démarrer tout l’environnement de développement local avec **une seule commande**.

## Commandes

| Commande | Effet |
|----------|--------|
| `npm run dev:all` | Prérequis → .env → deps → API :8000 → Vite :5173 → health → navigateur |
| `npm run dev:stop` | Arrêt propre (PIDs + libération ports) |
| `npm run dev:status` | Tableau de statut terminal |
| `start-elfis.bat` | Identique à `dev:all` (Windows) |
| `stop-elfis.bat` | Identique à `dev:stop` |
| `.\scripts\dev\elfis-launcher.ps1 -Watch` | Mode attaché (Ctrl+C = stop) |
| `.\scripts\dev\elfis-launcher.ps1 -SkipBrowser` | Sans ouverture navigateur |

## URLs

- App : http://localhost:5173/
- Login : http://localhost:5173/login
- **Cockpit Admin** : http://localhost:5173/elfadmin
- API health : http://127.0.0.1:8000/api/health
- Docs : http://127.0.0.1:8000/docs

## Prérequis

- Python 3 (venv backend)
- Node.js + npm
- Git
- `backend/.env` (obligatoire)
- `frontend/.env` (recommandé — Firebase)

## Runtime

Fichiers générés (gitignorés) dans `.elfis-dev/` :

- `pids.json` — PIDs session
- `backend.out.log` / `backend.err.log`
- `frontend.out.log` / `frontend.err.log`

## Notes

- Aucune logique métier modifiée.
- Ports alignés : backend **8000**, frontend **5173**, proxy Vite `/api` → `127.0.0.1:8000`.
- Les scripts historiques `start-backend.bat` / `start-frontend.bat` restent disponibles.
