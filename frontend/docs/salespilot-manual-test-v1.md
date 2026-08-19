# SalesPilot — procédure de test manuel V1 (PR1.1)

Recette fonctionnelle locale. **Aucun mot de passe réel** dans ce document.

## Prérequis

- Branche exécutée : `main` (ou branche de travail locale)
- Backend Python + frontend Vite
- Compte Firebase / org déjà créés en développement (ne pas committer d’identifiants)

## Démarrage

```bat
:: Terminal 1 — backend (depuis le dossier backend)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

:: Terminal 2 — frontend (depuis le dossier frontend)
npm run dev
```

Vérifier : `GET http://127.0.0.1:8000/api/health` → 200.

## Migrations SalesPilot

```bat
cd backend
python -m scripts.apply_salespilot_migrations
python -m scripts.apply_salespilot_migrations --report-only
```

Le CRM repose sur `create_all` + modèles ORM. Les SQL S1.6–S1.9 appliquent le DDL `IF NOT EXISTS` / `ALTER` sur Postgres persistant.

## Seed DEMO

```bat
cd backend
python -m scripts.seed_salespilot_demo
python -m scripts.seed_salespilot_demo --organization-id <ID>
python -m scripts.seed_salespilot_demo --purge
python -m scripts.seed_salespilot_demo --force
```

- Marqueur : `[DEMO SalesPilot]` / source `demo_salespilot`
- Interdit en `APP_ENV=production`
- Idempotent (≥ 8 leads DEMO → skip sans `--force`)

## Compte test

Utiliser le compte de développement local déjà provisionné (Firebase → JWT ELFIS).  
Ne pas documenter ni committer d’email/mot de passe.

## Parcours manuel minimal

1. Login → App Launcher → **SalesPilot** (bêta DEV) → `/sales`
2. Dashboard : KPI, pipeline overview, tâches, insights
3. Prospects / Entreprises / Contacts : listes non vides après seed
4. Pipeline : colonnes, déplacement (desktop) ou select (mobile)
5. Deal Workspace (`/sales/deals/:id`) : produits, participants, quick actions
6. Créer une proposition depuis un deal → lignes → readiness → PDF → revue → envoi → acceptation
7. Conversion : client → preview → confirmer (brouillon ComptaPilot)
8. Si multi-taux TVA : conversion **bloquée** avec message explicite (pas de taux silencieux)
9. Priorités commerciales : sync, acknowledge, dismiss
10. Équipe : membres, commentaires, followers, revues
11. Retour Launcher → ComptaPilot → `/dashboard`
12. Logout / login

## Smoke API

```bat
cd backend
set ELFIS_SMOKE_TOKEN=<jwt>
python -m scripts.smoke_salespilot --token %ELFIS_SMOKE_TOKEN%
```

## E2E

Playwright n’est **pas** dans le repo. Parcours E2E minimal = cette procédure + tests Vitest navigation/shell.  
Ne pas ajouter Playwright dans PR1.1.

## Nettoyage DEMO

```bat
python -m scripts.seed_salespilot_demo --purge
```

## Résultats attendus

| Surface | Attendu |
|---------|---------|
| Routes `/sales/*` listées | 200 UI, pas d’écran blanc |
| Seed | listes peuplées |
| Launcher DEV | SalesPilot bêta → `/sales` |
| Launcher prod | SalesPilot `coming_soon` |
| Multi-TVA | preview blocker + convert 409 `multi_vat_unsupported` |

## Erreurs connues / dette

Voir `frontend/docs/salespilot-pr1.1-anomalies.md` et le rapport d’audit PR1.1.
