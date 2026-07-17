# ComptaPilot IA — AI Finance Copilot

> Déposez une facture. L'IA prépare votre comptabilité.

Stack : **FastAPI + React + Firebase Auth + Cloud Firestore + stockage persistant Render**.

## Auth Firebase (obligatoire)

1. Console Firebase → **ELFIS Core** → **Ajouter une application** → Web  
2. **Authentication** → **Méthode de connexion** → activer **E-mail/mot de passe**  
3. Copier la config web dans `frontend/.env` (voir `frontend/.env.example`)  
4. Copier la **même clé API web** dans `backend/.env` :

```env
FIREBASE_WEB_API_KEY=...
FIREBASE_PROJECT_ID=...
AUTH_REQUIRED=true
```

5. Redémarrer backend (port **8001**) et frontend (port **5173**)

Créer un compte : http://127.0.0.1:5173/register  
Connexion : http://127.0.0.1:5173/login

## Cloud Firestore et photos

La base `(default)` du projet `elfis-core` est utilisée en région `eur3`.

- `users/{uid}` : profil synchronisé de l’utilisateur
- `organizations/{id}` : organisation active
- `organizations/{id}/members/{uid}` : rôle, permissions et statut
- disque persistant de l’API `/data/storage` : documents et photos de profil

Les règles temporaires ouvertes de la console ne doivent pas être conservées. Les règles sécurisées
sont dans `firestore.rules`. Pour les publier :

```bash
firebase login
firebase use elfis-core
firebase deploy --only firestore:rules,firestore:indexes
```

Un propriétaire ou administrateur peut ajouter un utilisateur déjà inscrit depuis
**Organisation → Utilisateurs et droits**.

## Déploiement

1. Construire le frontend : `cd frontend && npm ci && npm run build`
2. Définir `VITE_API_URL=https://votre-api.example/api` avant le build
3. Publier Hosting : `firebase deploy --only hosting`
4. Déployer `backend/Dockerfile` avec un volume persistant monté sur `/data`
5. Définir `APP_ENV=production`, un `JWT_SECRET` aléatoire d’au moins 32 caractères,
   les origines exactes dans `CORS_ORIGINS` et les variables Firebase

Après un push Git vers Render, `init_db` crée automatiquement les tables CRM
(`catalog_items`, `commercial_activities`) et les colonnes manquantes. Les routes
`/api/billing/customers`, `/catalog` et `/activities` nécessitent donc un redéploiement
backend pour être disponibles en production.

En production, l’API refuse de démarrer avec le secret JWT de développement, un CORS ouvert ou
une configuration Firebase absente.

## Stripe Billing — ComptaPilot Pro

L’offre SaaS unique est **ComptaPilot Pro à 19 € TTC/mois**, avec carte bancaire enregistrée au
départ et essai Stripe de 14 jours. Le backend démarre sans clés Stripe, mais les endpoints de
checkout et webhook répondent alors avec une erreur structurée `stripe_not_configured`.

1. Dans Stripe, créer un produit **ComptaPilot Pro** et un prix récurrent mensuel de **19,00 EUR**.
2. Renseigner dans `backend/.env` :

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_...
STRIPE_TRIAL_DAYS=14
STRIPE_PAST_DUE_GRACE_DAYS=3
FRONTEND_URL=http://localhost:5173
PLATFORM_ADMIN_EMAILS=admin@example.com
```

3. En local, installer Stripe CLI puis transférer les événements vers l’API :

```bash
stripe login
stripe listen --forward-to http://127.0.0.1:8001/api/subscriptions/webhook
```

Copier le secret `whsec_...` affiché par Stripe CLI. Pour un test complet, appeler
`POST /api/subscriptions/checkout` en tant que propriétaire/administrateur, puis utiliser la carte
de test Stripe `4242 4242 4242 4242`, une date future et un CVC quelconque.

En Test comme en Live, le webhook Stripe doit viser
`https://votre-api.example/api/subscriptions/webhook` et écouter :

- `checkout.session.completed`
- `customer.subscription.created`, `customer.subscription.updated`,
  `customer.subscription.deleted`
- `invoice.paid`, `invoice.payment_failed`

Les clés, prix et secrets webhook Test et Live sont distincts : avant le passage en Live, remplacer
ensemble `STRIPE_SECRET_KEY`, `STRIPE_PRICE_PRO` et `STRIPE_WEBHOOK_SECRET`. Stripe est la source de
vérité de l’état d’abonnement ; ne modifiez pas directement la table `subscriptions`.

Les routes métier renvoient une réponse structurée `402` si l’abonnement est absent/inactif.
Les routes auth, profil, organisation et abonnement restent accessibles afin de permettre la
connexion et la régularisation. Les adresses dans `PLATFORM_ADMIN_EMAILS` accèdent aux vues serveur
`/api/platform/*`, qui n’exposent aucune donnée de carte.

## Modules

| Module | Accès |
|---|---|
| Dashboard / Pilotage | `/` |
| Copilote IA | `/copilote` |
| Comptabilité | `/deposit`, `/history` |
| Facturation | `/facturation` |
| Banque | `/banque` |
| Trésorerie | `/tresorerie` |
| Organisation | `/organisation` |
| Mon compte | `/compte` |

## Démarrage

```bash
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8001

cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```
