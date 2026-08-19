# A1.1.1 — Aperçu facture & stabilisation envoi e-mail

Date : 2026-08-01  
Périmètre : Facturation → Aperçu → Envoi (pas A1.2, pas SalesPilot / Home / Launcher / Command Center)

## Cause exacte

1. **Doublon `SMTP_*` dans `backend/.env`** : un second bloc `SMTP_HOST=` (vide) écrasait `smtp-relay.brevo.com` (python-dotenv : dernière clé gagne).
2. **Credentials absents** : `SMTP_USER`, `SMTP_PASSWORD` et `BREVO_API_KEY` vides → `email_configured() == False` → UI mailto + bandeau « SMTP / Brevo non configuré ».
3. **Preview illisible** : legacy `.modal-panel` + règle Decision `max-width: 480px` (même sélecteur, plus tardive) → panneau ~480px.

`PLATFORM_EMAIL_FROM=documents@elfiscore.com` était déjà correct.

## Mode Brevo utilisé

**Mode A — SMTP** (`smtp-relay.brevo.com`) prioritaire si `SMTP_HOST` + `SMTP_USER` + `SMTP_PASSWORD` + From.  
**Mode B — API Brevo** (`xkeysib-…`) en secours.  
Pas de second mailer ajouté. Test org existant : `POST /api/org/email-settings/test`.

## Variables attendues (sans secrets)

| Variable | Rôle |
|----------|------|
| `SMTP_HOST` | `smtp-relay.brevo.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | login `…@smtp-brevo.com` |
| `SMTP_PASSWORD` | clé SMTP `xsmtpsib-…` |
| `SMTP_USE_TLS` | `true` |
| `BREVO_API_KEY` | clé API `xkeysib-…` (optionnel si SMTP OK) |
| `PLATFORM_EMAIL_FROM` | expéditeur vérifié |
| `PLATFORM_EMAIL_FROM_NAME` | nom From |

Ne jamais mettre ces clés dans `frontend/.env` ni le bundle.

Admin : renseigner SMTP (ou API) dans `backend/.env` / Render, **sans dupliquer** `SMTP_*`, redémarrer uvicorn. Diagnostic : `GET /api/health` + `GET /api/platform/email-status` (admin) → `/elfadmin/configuration`.

## Matrice flux (audit)

| Étape | Fichier | État | Cause | Correction |
|-------|---------|------|-------|------------|
| UI Envoyer | `SalesDocPreviewModal.tsx` | Corrigé | Message unique + modal 480px | Dialog DS + reason codes FR |
| API emails | `billing.py` | Corrigé | `can_send_direct` plateforme seule | + connexions sendable + flags mailer |
| Delivery | `document_delivery.py` | OK | — | Réutilisé |
| Mailer select | `mailer.py` | Corrigé | Env écrasé / raison opaque | `mailer_reason_code` / diagnostic |
| SMTP / Brevo | `mailer.py` | OK mode | Credentials manquants | Doc + `.env` sans doublon |
| PDF attach | `sales_email.py` | OK | — | Codes `attachment_missing` etc. |
| Vault | `document_delivery.py` | OK | — | Inchangé |
| Status / events | Event Bus + logs | OK | — | Pas de 2e historique |
| Notif user | handlers existants | OK | — | — |

## Preview

- `Dialog` Overlay Manager `size="full"` + `.sales-preview-dialog`
- Desktop : ~`min(1280px, 100vw-64px)` × `min(880px, 100vh-64px)`, PDF ~70 % / actions ~30 %
- Tablet/mobile : onglets Aperçu / Actions / Historique
- CTA : Modifier, Télécharger, Envoyer, Marquer payée, Relancer ; historique `email_logs` existant
- Mailto : download PDF + prefills ; jamais « pièce jointe via mailto » ni faux succès SMTP

## Mapping erreurs (extrait)

`provider_not_configured`, `missing_smtp_credentials`, `missing_api_key`, `sender_not_configured`, `sender_not_verified`, `authentication_failed`, `provider_unreachable`, `recipient_missing`, `recipient_invalid`, `attachment_missing`, `delivery_failed`, `timeout` → messages FR distincts (`mailerErrorMessages.ts`).

## Fichiers modifiés

- `backend/.env`, `backend/.env.example`
- `backend/app/services/mailer.py`, `sales_email.py`
- `backend/app/routers/billing.py`, `platform.py`, `main.py`
- `backend/tests/test_mailer.py`
- `frontend/src/components/SalesDocPreviewModal.tsx`
- `frontend/src/mailerErrorMessages.ts` (+ test)
- `frontend/src/api.ts`, `index.css`
- `frontend/src/pages/FacturationPage.tsx`, `DecisionDetailPage.tsx`

## Dette restante

- Renseigner credentials Brevo réels (Chris / ops) — non commitables
- Probe réseau Brevo seulement si clés présentes
- UI connexions e-mail org (Gmail/MS) encore peu exposée hors API

## GO / NO GO

**NO GO commercial envoi serveur** tant que `SMTP_USER`/`SMTP_PASSWORD` (ou `BREVO_API_KEY`) non renseignés et validés.  
**GO UX aperçu** après validation manuelle Chris (M01–M18).  
**GO technique câblage** : doublon env corrigé, diagnostics + messages différenciés, preview Dialog.

---

## TABLEAU A — Tests Cursor

| # | Test | Résultat | Preuve | Fichier | Commentaire |
|---|------|----------|--------|---------|-------------|
| 1 | Env SMTP host chargé | OK | `SMTP_HOST='smtp-relay.brevo.com'` | `.env` | Doublon retiré |
| 2 | `email_configured` sans creds | OK False | diagnostic | `mailer.py` | Attendu |
| 3 | `mailer_reason_code` | OK `missing_smtp_credentials` | python diag | `mailer.py` | Plus opaque |
| 4 | Transport none | OK | — | — | — |
| 5 | Priorité SMTP vs Brevo | OK tests | pytest | `test_mailer.py` | — |
| 6 | API Brevo mock send | OK | pytest | `test_mailer.py` | Pas d’envoi réel |
| 7 | Health mailer fields | OK code | `main.py` | reason_code exposé |
| 8 | Platform email-status | OK code | `platform.py` | Admin only |
| 9 | Billing flags | OK code | `billing.py` | mailer_* |
| 10 | can_send_direct + org conn | OK code | `billing.py` | sendable |
| 11 | Error codes normalisés | OK | `sales_email.py` | — |
| 12 | FE reason messages | OK | vitest | `mailerErrorMessages.test.ts` | — |
| 13 | Preview Dialog DS | OK code | `SalesDocPreviewModal.tsx` | Overlay Manager |
| 14 | CSS 480px conflict | OK | `index.css` | scoped Decision |
| 15 | Mailto no fake success | OK copy | modal | — |
| 16 | Compliance consent | OK | modal | unchecked |
| 17 | Mark paid / remind props | OK | FacturationPage | — |
| 18 | Pas de clé FE | OK | audit | — |
| 19 | Pas 2e mailer | OK | — | — |
| 20 | Org test endpoint exists | OK | `org_email.py` | Réutilisé |
| 21 | pytest mailer | OK 5/5 | pytest | `test_mailer.py` | — |
| 22 | vitest mailer messages | OK 2/2 | vitest | `mailerErrorMessages.test.ts` | — |
| 23 | tsc | OK | `tsc --noEmit` | — | — |
| 24 | build FE | OK | `npm run build` | — | — |
| 25 | Envoi réel | SKIP | — | Pas de destinataire test fourni |
| 26 | Secrets logs | OK | pas de dump | — |
| 27 | Vault path inchangé | OK | delivery tests 23 pass | `test_document_delivery.py` | — |
| 28 | Hors SalesPilot/Home | OK | — | — |
| 29 | Pas A1.2 | OK | STOP | — |
| 30 | Doc écrite | OK | ce fichier | — |
| — | overlays DS | OK 36 tests | vitest | overlay tests | — |
| — | sales billing | OK | pytest | `test_sales_billing.py` | — |

---

## TABLEAU B — Tests manuels Chris (M01–M18)

| ID | Étape | Résultat attendu | Résultat observé | Note/5 | Statut | Capture | Commentaire |
|----|-------|------------------|------------------|--------|--------|---------|-------------|
| M01 | Ouvrir aperçu facture | Dialog large, PDF lisible | — | — | À tester manuellement | — | — |
| M02 | Desktop 2 colonnes | PDF ~70 % / actions droite | — | — | À tester manuellement | — | — |
| M03 | Laptop quasi plein écran | Pas de micro-panneau | — | — | À tester manuellement | — | — |
| M04 | Tablette onglets | Aperçu / Actions / Historique | — | — | À tester manuellement | — | — |
| M05 | Mobile fullscreen | Header sticky, pas scroll H | — | — | À tester manuellement | — | — |
| M06 | Message config | Reason code adapté (pas texte unique) | — | — | À tester manuellement | — | — |
| M07 | Lien admin | `/elfadmin/configuration` | — | — | À tester manuellement | — | — |
| M08 | Mailto ack | Download + mailto, pas succès SMTP | — | — | À tester manuellement | — | — |
| M09 | Mentions manquantes | Liste SIRET/adresse + consent | — | — | À tester manuellement | — | — |
| M10 | CTA disabled | Pas d’envoi silencieux | — | — | À tester manuellement | — | — |
| M11 | Remplir SMTP + restart | `email_ready` true | — | — | À tester manuellement | — | Ops |
| M12 | Envoi test org | OK via settings test | — | — | À tester manuellement | — | Dest. explicite |
| M13 | Envoi facture serveur | PDF joint + Vault | — | — | À tester manuellement | — | Pas client réel |
| M14 | Historique logs | Même liste, status/code | — | — | À tester manuellement | — | — |
| M15 | Marquer payée | Ouvre paiement | — | — | À tester manuellement | — | — |
| M16 | Relancer | Action remind | — | — | À tester manuellement | — | — |
| M17 | Double-clic envoi | Idempotency / lock | — | — | À tester manuellement | — | — |
| M18 | Health sans secrets | JSON masqué | — | — | À tester manuellement | — | — |
