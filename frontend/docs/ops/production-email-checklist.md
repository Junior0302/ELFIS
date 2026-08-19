# Checklist production — e-mail plateforme (Brevo / SMTP)

Date : 2026-08-01  
Usage : cocher après chaque étape réelle (ops / Chris). Ne pas cocher par anticipation.

Références :

- Guide : [brevo-production-setup.md](./brevo-production-setup.md)
- Rapport : [email-production-readiness.md](./email-production-readiness.md)
- Remediation A1.1.1 : `../comptapilot/commercial-readiness/08-invoice-preview-email-delivery-remediation.md`

---

## Domaine & expéditeur Brevo

- [ ] **Domaine vérifié** — domaine d’envoi authentifié dans Brevo (SPF / DKIM selon console Brevo)
- [ ] **Adresse expéditrice validée** — `PLATFORM_EMAIL_FROM` (ex. `documents@elfiscore.com`) autorisée comme Sender chez Brevo

## Configuration serveur

- [ ] **Variables `.env`** — `SMTP_*` (Mode A) et/ou `BREVO_API_KEY` (Mode B) + `PLATFORM_EMAIL_FROM` / `PLATFORM_EMAIL_FROM_NAME` dans **backend** / Render uniquement ; **aucune** clé dans `frontend/.env` ; **pas de doublon** `SMTP_*` vide
- [ ] **Backend redémarré** — uvicorn / Manual Deploy après modification des env vars

## Diagnostic

- [ ] **Provider détecté** — `GET /api/health` : `email_ready: true`, `email_transport` = `smtp` ou `brevo`, `mailer_reason_code: ok` ; optionnel admin : `GET /api/platform/email-status` → `brevo_ok: true`

## Envoi de test (sans client réel)

- [ ] **Email de test** — `POST /api/org/email-settings/test` → message reçu sur la boîte de l’utilisateur connecté
- [ ] **PDF reçu** — envoi d’une facture / devis de **test interne** (destinataire non client) avec pièce jointe PDF ouverte correctement
- [ ] **Pièce jointe** — nom / contenu PDF cohérents avec le document ; pas d’échec `attachment_missing`

## Chaîne métier (post-config)

- [ ] **Vault** — document archivé / statut e-mail Vault mis à jour après envoi réussi
- [ ] **Historique** — entrée visible dans les logs e-mail du document (`email_logs` / UI aperçu)
- [ ] **Notification** — notification utilisateur / handlers existants déclenchés selon le flux
- [ ] **Statut Envoyé** — statut document / delivery = envoyé (pas faux succès mailto)

---

## Notes

| Étape | Preuve suggérée |
|-------|-----------------|
| Provider | Capturer JSON `details` de `/api/health` (sans secrets) |
| Test org | Réponse `{ "ok": true, "status": "sent" }` + mail reçu |
| PDF | Capture boîte mail + aperçu pièce jointe |
| Vault / historique | UI Facturation aperçu + Vault |

**GO commercial envoi serveur** uniquement lorsque **toutes** les cases ci-dessus sont cochées et validées.
