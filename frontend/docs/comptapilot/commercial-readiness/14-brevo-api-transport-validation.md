# 14 — Brevo API transport validation

## Verdict

| Critère | Statut |
|---------|--------|
| Sélection transport API avant SMTP | **GO** (corrigé) |
| Endpoint / PJ / sender / mapping erreurs | **GO** (code existant) |
| Clé API acceptée par Brevo | **NO GO** (HTTP **401** `Key not found`) |
| Test isolé d’envoi réel | **Non exécuté** (pas d’adresse de test fournie + clé refusée) |
| Parcours facture E2E | **Non exécuté** (prérequis isolé non rempli) |

**Décision phase : NO GO livraison** — le branchement API est correct, mais la clé `BREVO_API_KEY` runtime est **rejetée** par Brevo.

## 1. Lecture de `BREVO_API_KEY`

| Élément | Détail |
|---------|--------|
| Settings | `app.config.Settings.brevo_api_key` ← env `BREVO_API_KEY` |
| Fichier | `backend/.env` (dotenv ; pas d’override process env) |
| Nettoyage | `_clean_secret` dans le validateur Settings |
| Usable | `_brevo_api_key_usable()` : `xkeysib-…`, longueur > 40, **pas** `xsmtpsib-`, + `effective_platform_from` non vide |

Runtime observé (sans secret complet) :

- configurée = true  
- longueur = **55**  
- préfixe 10 = `xkeysib-2d`  
- forme xkeysib = true  

## 2. Ordre de sélection (avant / après)

**Avant :** `email_transport()` et `send_email()` tentaient **SMTP d’abord**, API en secours → avec SMTP_* encore présents, l’API n’était **jamais** le canal déclaré (`transport=smtp`).

**Après (fix minimal) :**

- `email_transport()` → `brevo` si API usable, sinon `smtp`
- `send_email()` → `_via_brevo()` d’abord, puis `_via_smtp()` en fallback

`dispatch_email` (connexion `platform`) appelle `send_email` — hérite de cet ordre.

Runtime après fix : `email_transport=brevo`.

## 3. Endpoint HTTP

`POST https://api.brevo.com/v3/smtp/email`  
Headers : `api-key`, `accept`, `content-type: application/json`  
(`app/services/mailer.py` → `_send_via_brevo`)

## 4. Pièce jointe PDF

Payload Brevo : `attachment[{ name, content }]` avec `content` = Base64 du PDF (`MailAttachment`).  
Couvert par tests unitaires (`test_send_email_via_brevo_uses_org_identity`, `test_send_email_prefers_brevo_api_over_smtp`).

## 5. Expéditeur

`PLATFORM_EMAIL_FROM` → `settings.platform_email_from` → `effective_platform_from`  
Runtime : **`contact@elfis-core.com`**  
Utilisé comme `sender.email` dans le payload API (sauf override explicite `sender_email`).

## 6. Mapping erreurs HTTP Brevo

| Condition | Message |
|-----------|---------|
| Clé `xsmtpsib-` dans `BREVO_API_KEY` | Erreur explicite « clé SMTP » |
| Préfixe hors `xkeysib-` | Clé invalide |
| `Key not found` / unauthorized | « Clé Brevo invalide ou absente » |
| Autre ≥400 | « Brevo a refusé l’envoi (detail) » |

Probe runtime API account : **HTTP 401**, message **`Key not found`**.

## 7. Secrets dans les logs

Diagnostics publics : préfixe / longueur / suffixe seulement (`email_status_public`).  
Aucun log de clé complète dans le chemin mailer normal.

## 8. Succès métier attendu (non atteint ici)

Sur succès API, le flux delivery enregistre :

- `provider=brevo`
- `provider_message_id` ← `messageId` Brevo
- `DocumentEmailLog.status=sent`
- Vault `email_status=sent` (archivage déjà fait avant l’envoi)

Non vérifié en réel faute de clé valide + destinataire test.

## Tests

- `tests/test_mailer.py` — **6 passed** (préférence API, endpoint, PJ, sender)
- Pas d’envoi réel à un client / facture `FAC-2026-0001`

## Test isolé / parcours facture

| Point | Décision |
|-------|----------|
| Adresse de test explicite utilisateur | **Absente** du brief |
| `POST /api/org/email-settings/test` | Envoie à l’email de l’utilisateur authentifié seulement (pas de `to=`) |
| Destinataire inventé | **Refusé** (règle) |
| Envoi isolé | Non lancé |
| Facture E2E | Non lancé |

## Cause NO GO livraison

1. Branchement corrigé → API sélectionnée (**OK**).  
2. Brevo refuse la clé runtime : **401 Key not found** (clé incomplète / révoquée / mauvais type malgré le préfixe `xkeysib-`).  
3. SMTP reste en fallback mais était déjà en **535** (A1.1.6) — double canal HS pour l’envoi réel.

## Déblocage (hors code)

1. Régénérer une **clé API** Brevo (`xkeysib-…`) complète dans Brevo → SMTP & API → API keys.  
2. Mettre à jour `BREVO_API_KEY` dans `backend/.env` (sans guillemets) ; redémarrer uvicorn.  
3. Fournir une **adresse de test** explicite, puis rejouer envoi isolé puis facture.
