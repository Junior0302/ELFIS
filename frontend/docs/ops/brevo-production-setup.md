# Guide d’installation — Brevo / SMTP (production)

Date : 2026-08-01  
Périmètre : configuration des credentials plateforme (pas de logique métier).  
Référence technique : `frontend/docs/comptapilot/commercial-readiness/08-invoice-preview-email-delivery-remediation.md`

---

## 1. Obtenir les credentials dans Brevo

1. Connexion au compte Brevo (https://app.brevo.com).
2. **SMTP & API** → section **SMTP** :
   - **Serveur** : `smtp-relay.brevo.com`
   - **Port** : `587` (STARTTLS)
   - **Login** : adresse du type `…@smtp-brevo.com` → c’est `SMTP_USER`
   - **Clé SMTP** : préfixe `xsmtpsib-…` → c’est `SMTP_PASSWORD` (pas `xkeysib-`)
3. Même écran → **Clés API** (optionnel, secours) :
   - Créer une clé API → préfixe `xkeysib-…` → c’est `BREVO_API_KEY`
4. Ne pas inverser les clés :
   - `xsmtpsib-` → uniquement `SMTP_PASSWORD`
   - `xkeysib-` → uniquement `BREVO_API_KEY`

**Mode recommandé (ELFIS Core)** : Mode A SMTP prioritaire ; Mode B API Brevo en secours si SMTP absente ou en échec.

---

## 2. Vérifier l’adresse expéditrice

1. Brevo → **Senders, Domains & Dedicated IPs** (ou équivalent).
2. Domaine `elfiscore.com` (ou domaine prod) : authentifié (SPF / DKIM selon Brevo).
3. Expéditeur autorisé : `documents@elfiscore.com` (valeur attendue côté plateforme).
4. Aligner `PLATFORM_EMAIL_FROM` sur une adresse **déjà validée** chez Brevo.
5. Nom d’affichage : `PLATFORM_EMAIL_FROM_NAME` (ex. `ComptaPilot`).

Sans expéditeur validé, l’envoi peut échouer avec `sender_not_verified` même si SMTP/API sont corrects.

---

## 3. Où placer chaque variable `.env`

**Uniquement** dans `backend/.env` (local) ou les variables d’environnement du service API (ex. Render → Environment).

| Variable | Obligatoire | Exemple (sans secret) |
|----------|-------------|------------------------|
| `SMTP_HOST` | Oui (Mode A) | `smtp-relay.brevo.com` |
| `SMTP_PORT` | Recommandé | `587` |
| `SMTP_USER` | Oui (Mode A) | `xxxxxx@smtp-brevo.com` |
| `SMTP_PASSWORD` | Oui (Mode A) | `xsmtpsib-…` |
| `SMTP_USE_TLS` | Recommandé | `true` |
| `PLATFORM_EMAIL_FROM` | Oui | `documents@elfiscore.com` |
| `PLATFORM_EMAIL_FROM_NAME` | Recommandé | `ComptaPilot` |
| `BREVO_API_KEY` | Optionnel si SMTP OK | `xkeysib-…` |
| `BREVO_WEBHOOK_SECRET` | Optionnel (webhooks) | chaîne opaque |
| `SMTP_FROM` | Alias seulement | vide si `PLATFORM_EMAIL_FROM` renseigné |

**Avertissements**

- Ne **jamais** mettre ces clés dans `frontend/.env` ni dans le bundle Vite.
- Ne **pas dupliquer** de blocs `SMTP_*` vides plus bas dans `.env` : python-dotenv garde la **dernière** occurrence (un `SMTP_HOST=` vide écrase le host Brevo).
- Coller les secrets **sans guillemets** ; après Save sur Render, faire un **Manual Deploy** / redémarrage process.

Modèle : `backend/.env.example` (lignes SMTP / Brevo).

---

## 4. Redémarrer le backend

Local :

```bash
# depuis backend/
# arrêter uvicorn puis relancer
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Render / hébergeur : redéploiement ou restart du service API après modification des env vars.

Le démarrage **n’échoue pas** si SMTP est manquant : le mailer reste désactivé jusqu’à configuration valide (voir rapport readiness).

---

## 5. Vérifier que la config est chargée

### Santé publique

`GET /api/health` → champ `details` :

| Champ | Attendu si OK |
|-------|----------------|
| `email_ready` | `true` |
| `email_transport` | `smtp` (idéal) ou `brevo` |
| `smtp_ready` | `true` en Mode A |
| `mailer_reason_code` | `ok` |
| `brevo_ok` | `true` (probe SMTP ou API) |
| `platform_email_from` | adresse From |

### Admin plateforme

`GET /api/platform/email-status` (admin ELFIS) — probe login SMTP / ping compte API, sans secrets en clair.  
UI : `/elfadmin/configuration`.

Indicateurs utiles : `smtp_ready`, `smtp_user_looks_brevo`, `smtp_password_looks_brevo`, `brevo_key_looks_valid`, `reason_code`, `hint`.

---

## 6. Envoyer un e-mail de test (sans facture client)

Endpoint existant :

`POST /api/org/email-settings/test`

- Auth : utilisateur org avec permission `settings.manage`
- Destinataire : **e-mail du compte connecté** (pas un client)
- Contenu : message `[TEST] Envoi ComptaPilot — …` **sans PDF document**
- Succès : `{ "ok": true, "status": "sent", … }`

Prérequis : `email_ready` / plateforme configurée.  
Ensuite seulement : test d’envoi facture (PDF) sur un destinataire de test interne, pas un vrai client.

---

## 7. Interpréter les erreurs (`reason_code`)

Messages UI : `frontend/src/mailerErrorMessages.ts`.

| Code | Signification ops |
|------|-------------------|
| `provider_not_configured` | Ni SMTP complet ni API Brevo usable |
| `missing_smtp_credentials` | `SMTP_HOST` / `USER` / `PASSWORD` incomplets |
| `missing_api_key` | `BREVO_API_KEY` absente, trop courte, ou clé `xsmtpsib-` collée par erreur |
| `sender_not_configured` | `PLATFORM_EMAIL_FROM` (et alias `SMTP_FROM`) vides |
| `sender_not_verified` | From non validé chez Brevo |
| `authentication_failed` | 535 SMTP ou clé API refusée |
| `provider_unreachable` | Réseau / timeout vers Brevo |
| `recipient_missing` / `recipient_invalid` | Destinataire |
| `attachment_missing` | PDF non généré (flux facture) |
| `delivery_failed` | Refus fournisseur / échec générique |
| `timeout` | Délai dépassé |
| `ok` | Config / probe OK |

Pas de stacktrace utilisateur : les erreurs sont normalisées côté `sales_email` / UI.

---

## Checklist rapide post-config

1. Variables renseignées **une seule fois** dans `backend/.env` / Render  
2. Backend redémarré  
3. `GET /api/health` → `email_ready: true`, `mailer_reason_code: ok`  
4. `POST /api/org/email-settings/test` → reçu en boîte  
5. (Optionnel) envoi facture test interne + PDF joint  

Suite ops : `production-email-checklist.md` · décision : `email-production-readiness.md`.
