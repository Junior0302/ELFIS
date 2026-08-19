# ELFIS Developer Launcher V1 — Certification Report

**Date :** 2026-07-24  
**Scope :** Orchestration locale uniquement (aucune logique métier)

## Livrables

| Fichier | Rôle |
|---------|------|
| `package.json` (racine) | `npm run dev:all` / `dev:stop` / `dev:status` |
| `scripts/dev/elfis-launcher.ps1` | Prérequis, .env, deps, start, health, dashboard, navigateur |
| `scripts/dev/elfis-stop.ps1` | Arrêt PIDs + libération ports 8000/5173 |
| `scripts/dev/elfis-status.ps1` | Statut terminal |
| `start-elfis.bat` / `stop-elfis.bat` | Wrappers Windows |
| `docs/dev/elfis-developer-launcher-v1.md` | Documentation |
| `frontend/package.json` | Alias `dev:all` / `dev:stop` vers la racine |

## Vérifications effectuées

| Check | Résultat |
|-------|----------|
| Python / Node / npm / Git | OK |
| `backend/.env` + `frontend/.env` | OK |
| venv + uvicorn / node_modules | OK |
| Backend `:8000` | UP |
| Frontend `:5173` | UP |
| `GET /api/health` | 200 |
| Proxy `localhost:5173/api/health` | 200 |
| `GET /api/auth/me` | 401 (auth active) |
| `GET /api/platform/dashboard` | 401 (route présente) |
| Dashboard terminal + URL Cockpit `/elfadmin` | OK |
| `npm run dev:stop` libère ports | OK |

## Commandes certifiées

```bash
npm run dev:all
npm run dev:status
npm run dev:stop
start-elfis.bat
stop-elfis.bat
```

## Limites

- Mode par défaut **détaché** (services survivent après le script) ; `-Watch` pour session attachée.
- Ouverture navigateur dépend de l’association Windows HTTP.
- Ne crée pas automatiquement `backend/.env` (volontaire — secrets).

## Verdict

**ELFIS DEVELOPER LAUNCHER V1 CERTIFIED**
