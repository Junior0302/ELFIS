# ComptaPilot IA — AI Finance Copilot

> Déposez une facture. L'IA prépare votre comptabilité.

Stack : **FastAPI + React + Firebase Auth + Cloud Firestore + Firebase Storage**.

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
- Firebase Storage `avatars/{uid}/...` : photos de profil

Les règles temporaires ouvertes de la console ne doivent pas être conservées. Les règles sécurisées
sont dans `firestore.rules` et `storage.rules`. Pour les publier :

```bash
firebase login
firebase use elfis-core
firebase deploy --only firestore:rules,firestore:indexes,storage
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

En production, l’API refuse de démarrer avec le secret JWT de développement, un CORS ouvert ou
une configuration Firebase absente.

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
