# 12 — First commercial email validation (A1.1.6)

## Verdict

**NO GO** — la chaîne PDF → Vault est opérationnelle ; l’envoi SMTP Brevo échoue sur **authentification 535**. Aucun e-mail commercial réel n’a été livré.

## Objectif

Valider le premier envoi facture bout-en-bout :

`Créer facture → PDF → Vault archive → SMTP/Brevo → réception → historique → email_status=sent`

Sans nouvelle feature produit. Sans faux succès.

## Composants audités

| Composant | Fichier / endpoint | État |
|-----------|-------------------|------|
| PDF | `app/services/sales_pdf.py` (`sales_document_to_pdf`) | OK |
| Vault upload | `VaultStorageService` → bucket `elfis-vault` | OK (A1.1.5) |
| Checksum | `checksum_service.calculate_sha256` | OK |
| Signed URL | `create_signed_download_url` | OK (hors chemin SMTP : PJ = bytes PDF) |
| Mailer | `app/services/mailer.py` — transport **SMTP** `smtp-relay.brevo.com:587` | **KO auth** |
| Attachment | `MailAttachment` + `send_sales_document_email` | Préparé, non livré |
| History | `DocumentEmailLog` + Vault `email_status` | Non confirmé en réel (bloqué avant) |
| Test org email | `POST /api/org/email-settings/test` | Existe (destinataire = email user auth) |

## Config vérifiée (noms / flags seulement)

- `email_configured` = true (variables présentes)
- `email_transport` = `smtp` (pas d’API Brevo : `BREVO_API_KEY` vide)
- `SMTP_HOST` = `smtp-relay.brevo.com`
- `SMTP_PORT` = 587 / TLS = true
- `SMTP_USER` forme `@smtp-brevo.com` = true
- `SMTP_PASSWORD` forme `xsmtpsib-` = true
- `PLATFORM_EMAIL_FROM` domaine = `elfis-core.com`
- `SUPABASE_URL` / service role / `ELFIS_VAULT_BUCKET=elfis-vault` = OK
- Health runtime (`GET /api/health`) : `mailer_provider_reachable=false`, `mailer_reason_code=authentication_failed`

## Exécution runtime (chaîne réelle)

| Champ | Valeur |
|-------|--------|
| Date (UTC) | 2026-08-01T15:53:29Z |
| Durée | ~2,1 s |
| Destinataire | domaine plateforme `elfis-core.com` (auto-test, pas un client) |
| Document | `FAC-2026-0001` (PDF généré, 2323 octets, `%PDF`) |

### Résultat par étape

| Étape | Résultat | Détail |
|------|----------|--------|
| PDF_CREATED | ✓ | `sales_document_to_pdf`, size=2323 |
| CHECKSUM | ✓ | sha256 préfixe `454c153c2b89` |
| VAULT_UPLOAD_SUCCESS | ✓ | bucket `elfis-vault`, path diagnostic |
| SIGNED_URL_CREATED | ✓ | URL http, len≈455 |
| VAULT_DOWNLOAD | ✓ | bytes == upload |
| EMAIL_SENT | ✗ | **SMTP auth 535** |
| ATTACHMENT | préparée, non livrée | `FAC-2026-0001.pdf` |
| SUBJECT / BODY | préparés | non remis |
| History / email_status=sent | ✗ | non atteint (échec provider) |
| Rollback Vault | N/A | objet diagnostic nettoyé ; pas de rollback métier email |

### Erreur réelle (EMAIL_SENT)

| Champ | Valeur |
|-------|--------|
| Code / classification | `smtp_auth_failed` / SMTP **535** `5.7.8 Authentication failed` |
| Composant | `mailer_smtp` (`_send_via_smtp`) |
| Message clair | Auth SMTP Brevo refusée (535). Login masqué `…@smtp-brevo.com`. Clé `xsmtpsib-` de forme OK mais **refusée** (obsolète/incomplète ou filtrage IP SMTP Brevo). |
| Ce que ce n’est pas | Pas Vault, pas PDF, pas « Service temporairement indisponible » ambigu |

## Logging ajouté (minimal)

Dans `document_delivery.py` :

`PDF_CREATED` → `VAULT_UPLOAD_SUCCESS` → `EMAIL_SENT` / `EMAIL_FAILED` → `EMAIL_CONFIRMED`

Sans secrets, sans contenu PDF. Champ structuré `delivery_step`.

Note : le chemin d’envoi commercial attache le PDF en bytes ; `SIGNED_URL_CREATED` est validé côté Vault (consultation) mais n’est pas une étape SMTP.

## Tests automatisés

- `tests/functional/scenarios/test_phase_d_a116_email_validation.py`
  - chaîne mockée : steps loggés, historique, `email_status=sent`
  - message d’auth SMTP 535 explicite (pas de secret dans l’exception)
- Phase D existante (`test_phase_d_delivery.py`) conserve le chemin mock mailer

## GO / NO GO

| Critère | Statut |
|---------|--------|
| PDF généré | GO |
| Vault upload + checksum + signed URL + download | GO |
| SMTP / Brevo envoi réel | **NO GO** (535) |
| Attachment remis | NO GO |
| History / status sent réel | NO GO |
| Premier e-mail commercial livré | **NO GO** |

**Décision A1.1.6 : NO GO**

### Déblocage requis (hors scope code de cette phase)

1. Régénérer la clé SMTP Brevo (`xsmtpsib-…`) et mettre à jour `SMTP_PASSWORD` (et éventuellement `SMTP_USER`).
2. Ou configurer `BREVO_API_KEY` (`xkeysib-…`) + expéditeur vérifié.
3. Vérifier qu’aucun allowlist IP SMTP Brevo ne bloque l’environnement local / Render.
4. Rejouer ce rapport jusqu’à `EMAIL_CONFIRMED` + `email_status=sent` sur un destinataire de test.
