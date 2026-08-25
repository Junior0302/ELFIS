# Runbook — Investor demo ELFIS Core

Déploiement public HTTPS pour une démonstration investisseurs.
Chemin : **Firebase Hosting** (frontend) + **Render** (API Docker) + **PostgreSQL managé**.

Ne pas coller de secrets dans ce fichier. Ne pas activer de faux credentials Bridge / Brevo / Stripe.

## Limites assumées

- Aucun worker Render. Les files jobs/events existent en base mais **ne sont pas consommées**.
- Une action asynchrone (analyse IA, indexation, e-mail plateforme) ne doit jamais s’afficher comme terminée.
- `ELFIS_AI_ENABLED=false`, `ELFIS_OCR_ENABLED=false`, `ELFIS_BILLING_ENABLED=false`.
- Bridge / Brevo / SMTP / Stripe : laisser vides. L’UI affiche un état non configuré.
- `ELFIS_DEMO_BANK_ENABLED=true` uniquement pour montrer le Banking avec le libellé **Banque Démo ELFIS — données fictives**.
- BANK-4 (sync auto planifiée) est hors scope.

## 1. Créer PostgreSQL

1. Appliquer le blueprint `render.yaml` (crée `elfis-core-db`) **ou** créer une base PostgreSQL Render à la main dans la même région que l’API (Francfort).
2. Ne pas ouvrir la base au public (`ipAllowList` vide dans le blueprint).
3. Noter que `DATABASE_URL` sera injecté via `fromDatabase.connectionString` — aucun mot de passe dans Git.
4. Si le lien blueprint échoue : Dashboard Render → service API → Environment → `DATABASE_URL` = connection string interne Render (secret).

SQLite interdit. Aucun reset de base.

## 2. Configurer les secrets Render

Sur le service `elfis-core-api`, renseigner **uniquement** dans le dashboard :

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | déjà lié si blueprint OK |
| `JWT_SECRET` | généré (`generateValue`) ou collé (≥ 32) |
| `FIREBASE_WEB_API_KEY` | clé **web** Firebase (même que `VITE_FIREBASE_API_KEY`) |
| `FIREBASE_PROJECT_ID` | id projet Firebase |
| `CORS_ORIGINS` | origines HTTPS exactes du front, séparées par des virgules |
| `FRONTEND_URL` | URL HTTPS canonique du front |
| `PUBLIC_API_URL` | URL HTTPS publique de l’API |
| `PLATFORM_ADMIN_EMAILS` | e-mails super-admin (comptes déjà / à inscrire via Firebase) |

Laisser vides : Stripe, OpenAI, Brevo, SMTP, Bridge, Supabase.

Vérifier les flags : `ELFIS_ENVIRONMENT=production`, `ELFIS_BILLING_ENABLED=false`, workers `false`, `ELFIS_DEMO_BANK_ENABLED=true`, `STORAGE_PROVIDER=local`, `STORAGE_DIR=/data/storage`.

Disque : mount `/data` (déjà dans le blueprint).

## 3. Migrer la DB

**Avant** le premier trafic. `upgrade_head` est additif (`IF NOT EXISTS`), pas un reset.

Le blueprint déclare :

```text
preDeployCommand: python -m scripts.rc1.migrate_sql
```

Cette commande lit `DATABASE_URL` et appelle `scripts.rc1.migrate_sql.upgrade_head` (inclut BANK-2, BANK-3 et BANK-3.1 via `SQL_ORDER`).

Si la pre-deploy Docker n’est pas exécutée par Render, lancer **une fois** depuis le Shell du service (image déjà construite) :

```bash
python -m scripts.rc1.migrate_sql
```

Depuis un checkout local (jamais logger l’URL) :

```bash
cd backend
# DATABASE_URL déjà exporté dans le shell, valeur non commitée
python -m scripts.rc1.migrate_sql
```

Attendu : JSON `ok: true`, `alembic: false`. SQLite → code de sortie 2.

Ne pas appeler `upgrade_head` au boot de chaque instance : `init_db()` ne fait que `create_all`.

## 4. Déployer l’API

1. Dashboard Render → `elfis-core-api` → Manual Deploy (le blueprint a `autoDeploy: false`).
2. Image : `backend/Dockerfile` (Uvicorn `:8001`).
3. Confirmer le disque `/data` et l’utilisateur `appuser`.

## 5. Vérifier health

```bash
curl -sS https://<api-publique>/api/health/live
curl -sS https://<api-publique>/api/health/ready
curl -sS https://<api-publique>/api/health
```

Attendu :

- `live` → 200 `{ "status": "ok", "check": "live" }`
- `ready` → 200 `ok` ou `degraded` (Vault cloud optionnel)
- `health` → 200 minimal, **sans** préfixe/longueur de clé, host SMTP, ni détail mailer
- `/docs`, `/redoc`, `/openapi.json` absents

## 6. Variables Vite

Build-time uniquement (jamais dans Firebase Hosting env après coup) :

```text
VITE_API_URL=https://<api-publique>/api
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_APP_ID=
```

Sans `VITE_API_URL` HTTPS, `npm run build` **échoue**. Aucun fallback `https://<front>:8000/api`.

## 7. Build frontend

```bash
cd frontend
npm ci
npm run build
```

Sortie : `frontend/dist`.

## 8. Firebase deploy

`firebase.json` réécrit déjà `**` → `/index.html` (refresh `/platform/banking` OK).

```bash
firebase use elfis-core
firebase deploy --only hosting
```

Option : déployer aussi `firestore:rules` / indexes si pas déjà en place.

## 9. Domaine Firebase Auth autorisé

Console Firebase → Authentication → Settings → Authorized domains :

- `elfis-core.web.app`
- `elfis-core.firebaseapp.com`
- le domaine custom (`demo.elfis-core.com`) **avant** de l’utiliser

## 10. CORS backend

`CORS_ORIGINS` et `FRONTEND_URL` doivent lister **exactement** l’origine HTTPS du front (schéma + hôte, sans chemin).

Pas de `*`. Pas de `localhost` en production.

Après changement : redéployer ou redémarrer l’API.

## 11. Smoke tests

1. HTTPS landing `/`
2. `/register` puis `/login` (Firebase e-mail / mot de passe)
3. `/home` (Espaces)
4. Refresh dur : `/finance`, `/documents`, `/facturation`, `/platform/banking`
5. Banking : Bridge = configuration requise ; démo = libellé fictif si activée
6. Envoi e-mail facture : refus propre, pas « envoyé »
7. Checkout Stripe : indisponible / non configuré, pas de faux paiement
8. `GET /api/health` sans fuite mailer
9. Origine inconnue : pas de header CORS

## Phase 2 — commandes opératoires

Voir la fin du compte-rendu Phase 1. Ne rien déployer tant que les secrets dashboard et le build Vite ne sont pas prêts.
