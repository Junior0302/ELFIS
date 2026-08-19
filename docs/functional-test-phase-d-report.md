# Rapport Phase D — Validation comptable, documents commerciaux, Delivery, e-mail, notifications, Search

Date : 2026-07-20  
Environnement : `ELFIS_ENVIRONMENT=test` · MockMailer via patch `httpx` · stockage Vault mock  
Commande : `python scripts/run_functional_validation.py --phase-d`  
Commit / push : **aucun**

---

## 1. Cartographie validation et Delivery

```
Proposition ready_for_validation|requires_review
  → POST /api/accounting/proposals/{id}/validate
      (confirm_balanced_entry + confirm_document_reviewed)
  → entry validated · review · event accounting.proposal.validated.v1
  → notification + job search index (best effort)

Proposition → POST .../reject { reason }
  → rejected · event accounting.proposal.rejected.v1
  → aucune écriture finale « sent » supplémentaire

Facture/Devis (SalesDocument)
  → GET /api/billing/documents/{id} · /pdf
  → POST /api/billing/documents/{id}/email { recipient, subject, body, send_mode: server }
  → DocumentDeliveryService.send_document
      → entitlement email.send · quota emails.sent.month
      → PDF généré · archive_or_reuse_pdf (Vault)
      → send_sales_document_email (mailer Brevo/SMTP via dispatch)
      → events delivery.email.started|sent|failed.v1
      → notification · historique DocumentEmailLog
```

Expéditeurs : `GET /api/professional-emails/sender-options` · demande `POST /request` · admin activate/reject.

---

## 2. Routes auditées

| Domaine | Routes |
|---------|--------|
| Accounting | proposals list/get, validate, reject, reopen |
| Billing docs | documents CRUD light, pdf, email, emails, send (statut) |
| Professional emails | /me, /sender-options, /request, admin/* |
| Notifications | /api/notifications* |
| Search | /api/search, suggestions, platform reindex |
| Platform accounting | /api/platform/accounting/* (lecture) |

---

## 3. Documents commerciaux testés

- Facture client (`doc_type=facture`) : métadonnées, PDF, envoi mock.
- Devis (`doc_type=devis`) : idem.
- Document autre tenant : refus 403/404.
- Document absent : 404.

---

## 4. Modes expéditeur testés

| Mode | Résultat |
|------|----------|
| Options personnelles / org | `sender-options` sans secret SMTP |
| Demande ELFIS pending | créée ; non utilisable comme From usurpée |
| Activation admin | flux service existant (tests unitaires + route montée) |
| Infra e-mail réelle | **non créée** — mock uniquement |

---

## 5. Politique pièces jointes

- PDF généré côté serveur puis `archive_or_reuse_pdf` (checksum) → **pas de second blob** si réutilisation.
- L’utilisateur ne retéléverse pas la facture/devis depuis la fiche.
- Aucune storage key interne exposée au frontend dans les tests Phase D.
- PDF absent / erreur → `email_failed` ou 400 contrôlé ; document métier conservé.

---

## 6. Politique retries

- **Pas de worker retry Delivery automatique** en V1.
- Échec mailer → HTTP **200** + `status=email_failed` (document archivé, retry possible).
- Retry manuel = nouvel appel HTTP avec **nouvelle** `idempotency_key`.
- Même clé → `already_sent` / pas de second appel mailer.
- Limite exactly-once externe : si le provider accepte puis timeout côté client, un second envoi avec une autre clé reste possible (documenté).

---

## 7. Notifications

Types couverts par handlers existants : proposition ready / requires_review / validated / rejected ; delivery sent / failed.  
`action_url` relatifs (`/accounting/proposals/...`, `/documents`, `/facturation`).  
Isolation tenant vérifiée (NOTIF-004).

---

## 8. Indexation Search

Réindexation via events accounting validated/rejected/updated/ready.  
**Pas** de réindex sur `reopened.v1` ni sur `delivery.email.*` ; vault indexé surtout sur `archived` (pas `reused`).  
Search = best effort (échec indexation ne casse pas le métier).

---

## 9. Anomalies

### PHD-D-001 — Router professional-emails non monté

| Champ | Valeur |
|-------|--------|
| **Sévérité** | HIGH |
| **Cause** | `professional_emails.router` défini mais absent de `main.py` → 404 |
| **Correction** | `app.include_router(professional_emails.router, prefix="/api")` |
| **Test** | `test_sender_*` |
| **Résultat** | PASS |

### PHD-D-002 — Erreurs e-mail renvoyaient le texte brut provider

| Champ | Valeur |
|-------|--------|
| **Sévérité** | CRITICAL |
| **Cause** | `_user_facing_error` fallback = `str(exc)` (clés, secrets, stack) |
| **Correction** | Messages génériques ; plus d’écho du texte exception |
| **Test** | `test_obs_002_error_body_filtered` |
| **Résultat** | PASS |

### PHD-D-003 — Demande adresse ELFIS exposait `email_status_public`

| Champ | Valeur |
|-------|--------|
| **Sévérité** | CRITICAL |
| **Cause** | `notify` incluait fragments de clé Brevo / `has_smtp_password` |
| **Correction** | Réponse client limitée à flags sûrs (`admin_notified`, `mail_configured`, `error=notification_failed`) |
| **Test** | `test_sender_003_004_elfis_request_flow` |
| **Résultat** | PASS |

---

## 10. Corrections

| Fichier | Changement |
|---------|------------|
| `app/main.py` | Montage router professional-emails |
| `app/services/sales_email.py` | Sanitisation `_user_facing_error` |
| `app/routers/professional_emails.py` | Notify client sans secrets |
| `scripts/run_functional_validation.py` | Flag `--phase-d` |

---

## 11–13. Fichiers créés / modifiés / tests

**Créés** : `tests/functional/helpers/phase_d.py` ; 15 scénarios `test_phase_d_*.py` ; ce rapport.

**Modifiés** : `main.py`, `sales_email.py`, `professional_emails.py`, `run_functional_validation.py`, `functional-testing-checklist.md`.

**Tests** : VAL / REJECT / DOC / ATTACH / SENDER / MAIL / RETRY / IDEMP / NOTIF / SEARCH / HIST / SEC / OBS (42 tests fonctionnels Phase D).

---

## 14–18. Résultats

```
Accounting validation.......... PASS
Accounting rejection........... PASS
Commercial documents........... PASS
Automatic attachments.......... PASS
Sender selection............... PASS
Email delivery................. PASS
Delivery retries............... PASS
Delivery idempotency........... PASS
Email entitlements / quotas.... PASS
Notifications.................. PASS
Search synchronization......... PASS
History........................ PASS
Tenant isolation............... PASS
Security / observability....... PASS

Phase D functional tests........ 42 passed
Regression tests............... 130 passed (accounting+notif+search+delivery+mailer+jobs+events)
FastAPI import................. OK (250 routes)
Frontend build................. OK
Real emails sent............... 0
Known critical delivery issues. 0
```

---

## 19–20. Risques résiduels / limites

- Exactly-once strict avec Brevo non garanti (timeout après acceptation provider).
- Retry Delivery = manuel + nouvelle clé d’idempotence.
- Quota consommé au début de `send_document` (politique existante) — échec définitif peut avoir consommé ; non modifié dans cette phase.
- Search best effort ; pas d’index delivery.email.*.
- `MockMailerProvider` (fixture) non branché au runtime : les tests patchent `mailer.httpx.post`.

---

## 21. Tests manuels

Voir bloc **PHASE D** dans `docs/functional-testing-checklist.md` (D-UI-01 … D-UI-30).

---

## 22–23. Git

Aucun commit. Aucun push.
