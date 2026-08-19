# Rapport — Production Readiness e-mail (Sprint 1 Brevo / SMTP)

Date : 2026-08-01  
Sprint : Production Readiness 1 — configuration Brevo / SMTP  
Périmètre : audit + documentation uniquement (pas de changement métier).  
Référence A1.1.1 : `frontend/docs/comptapilot/commercial-readiness/08-invoice-preview-email-delivery-remediation.md`

---

## 1. État actuel

| Élément | État |
|---------|------|
| Flux d’envoi (A1.1.1) | Prêt — pas de faux succès, erreurs normalisées |
| Sélection transport | Mode A **SMTP** prioritaire ; Mode B **API Brevo** secours (`mailer.py`) |
| Credentials réels | **Non renseignés** (ou incomplets) côté ops — blocage commercial |
| Doublon `.env` SMTP | Corrigé en A1.1.1 (ne pas réintroduire) |
| Diagnostics | `GET /api/health`, `GET /api/platform/email-status`, UI `/elfadmin/configuration` |
| Test sans facture client | Existant : `POST /api/org/email-settings/test` |
| Startup fatal si SMTP manquant | **Non** — backend démarre ; mailer désactivé |

**Décision Sprint 1** : **GO CONFIGURATION** — le code est prêt à recevoir les credentials ; l’action restante est purement ops (Brevo + `.env` + vérifs checklist).

*(Le GO commercial envoi serveur reste conditionné au remplissage validé des credentials — hors scope de ce sprint.)*

---

## 2. Audit variables — utilisées réellement par le backend

Source : `backend/app/config.py`, `backend/app/services/mailer.py`, `backend/.env.example`, webhooks Brevo.

### Plateforme (transactionnel ComptaPilot / documents)

| Variable | Obligatoire | Description | Exemple (sans secret) |
|----------|-------------|-------------|------------------------|
| `SMTP_HOST` | Oui pour Mode A | Relais SMTP Brevo | `smtp-relay.brevo.com` |
| `SMTP_PORT` | Non (défaut 587) | Port SMTP | `587` |
| `SMTP_USER` | Oui pour Mode A | Login Brevo SMTP | `login@smtp-brevo.com` |
| `SMTP_PASSWORD` | Oui pour Mode A | Clé SMTP Brevo | `xsmtpsib-…` |
| `SMTP_USE_TLS` | Non (défaut true) | STARTTLS | `true` |
| `PLATFORM_EMAIL_FROM` | Oui | Expéditeur authentifié | `documents@elfiscore.com` |
| `PLATFORM_EMAIL_FROM_NAME` | Non (défaut ComptaPilot) | Nom From | `ComptaPilot` |
| `SMTP_FROM` | Non | Alias si `PLATFORM_EMAIL_FROM` vide | (vide recommandé) |
| `BREVO_API_KEY` | Non si Mode A OK | Clé API HTTPS Brevo | `xkeysib-…` |
| `BREVO_WEBHOOK_SECRET` | Non | Secret webhook delivery/bounce | chaîne opaque |

**Règle de readiness** (`email_configured()` / `_smtp_ready()`) :

- Mode A : `SMTP_HOST` + `SMTP_USER` + `SMTP_PASSWORD` + From effectif (`PLATFORM_EMAIL_FROM` ou `SMTP_FROM`)
- Mode B : `BREVO_API_KEY` usable (`xkeysib-…`, longueur > 40) + From effectif

### Hors mailer plateforme (ne pas confondre)

| Variable | Rôle |
|----------|------|
| `EMAIL_CREDENTIALS_ENCRYPTION_KEY` | Chiffrement connexions OAuth / SMTP **org** |
| `GOOGLE_*` / `MICROSOFT_*` | Connexions boîtes org (Gmail / Graph) — pas Brevo plateforme |

Ces variables ne remplacent pas SMTP/API plateforme pour l’envoi serveur par défaut.

---

## 3. Validation au démarrage — comportement réel

Fichier : `backend/app/security/security_startup.py` (`assert_startup_configuration`).

| Comportement | Réalité |
|--------------|---------|
| Refuse le start si SMTP manquant | **Non** — aucune issue fatale liée à Brevo/SMTP |
| Mailer désactivé si incomplets | **Oui** — `email_configured() == False`, transport `none` |
| Message utilisateur stacktrace | **Non** — reason codes + messages FR (`mailerErrorMessages.ts`) |
| Log startup type ✓ SMTP / ✗ PASSWORD | **Absent** au boot — diagnostic via health / admin |

**Health** (`GET /api/health`) expose déjà : `email_ready`, `email_transport`, `smtp_ready`, `mailer_reason_code`, `brevo_ok`, `brevo_error`, `email_hint` (pas de secrets en clair).

**Admin** (`GET /api/platform/email-status`) : probe SMTP login ou ping API + `hint` / `reason_code`.

Écart non bloquant : pas de ligne de log explicite au lifespan. Les endpoints existants suffisent pour l’ops ; **aucun correctif code** dans ce sprint (comportement déjà adéquat).

---

## 4. Prêt / restant à configurer

### Ready (technique)

- [x] Priorité SMTP → API
- [x] Diagnostics health + platform
- [x] Reason codes normalisés (UI + API)
- [x] Endpoint test org sans PDF document
- [x] Doc `.env.example` alignée
- [x] Guides ops (ce dossier)

### Remaining (ops)

- [ ] Credentials Brevo réels (`SMTP_USER` / `SMTP_PASSWORD` et/ou `BREVO_API_KEY`)
- [ ] Confirmation domaine + sender vérifiés dans Brevo
- [ ] Restart + `email_ready: true`
- [ ] Exécution checklist `production-email-checklist.md`
- [ ] Envoi réel validé (test org puis PDF interne)

---

## 5. Mode test — procédure existante

| Méthode | Existe ? | Usage |
|---------|----------|--------|
| `POST /api/org/email-settings/test` | **Oui** | E-mail `[TEST]` vers l’utilisateur connecté, sans document client |
| `GET /api/platform/email-status` | **Oui** | Probe auth SMTP / API sans envoi |
| Script CLI dédié | **Non** | — |
| Endpoint admin « send test to arbitrary address » | **Non** | — |

### Plan seulement (si besoin futur — ne pas développer maintenant)

1. Endpoint admin `POST /api/platform/email-test` avec destinataire allowlisté + rate limit  
2. Ou script `backend/scripts/probe_smtp.py` lecture settings + login SMTP + message minimal  
3. Logs structurés au startup (`✓ SMTP configuré` / `✗ SMTP_PASSWORD manquant`) — cosmétique  

Hors scope Sprint 1.

---

## 6. Risques

| Risque | Mitigation |
|--------|------------|
| Doublon `SMTP_*` vide dans `.env` | Une seule occurrence ; vérifier `.env.example` / Render |
| Confusion `xsmtpsib-` vs `xkeysib-` | SMTP_PASSWORD vs BREVO_API_KEY ; health signale `brevo_key_is_smtp_key_by_mistake` |
| From non vérifié Brevo | Valider sender avant envoi client |
| Secrets dans frontend | Interdit — audit A1.1.1 OK |
| Probe réseau sur chaque `/api/health` | Latence possible ; acceptable pour ops ; ne pas exposer publiquement sans rate limit hébergeur |
| IP SMTP Brevo restreintes | Désactiver Authorized IPs ou whitelister Render |

---

## 7. Décision

# GO CONFIGURATION

Le câblage backend/UI est prêt. Sprint suivant ops : renseigner les credentials Brevo selon [brevo-production-setup.md](./brevo-production-setup.md), cocher [production-email-checklist.md](./production-email-checklist.md), puis seulement décider du GO commercial envoi serveur.

**NO GO** commercial envoi serveur tant que credentials non validés (inchangé vs A1.1.1).

---

## 8. Livrables ce sprint

| Doc | Chemin |
|-----|--------|
| Guide install | `frontend/docs/ops/brevo-production-setup.md` |
| Checklist | `frontend/docs/ops/production-email-checklist.md` |
| Ce rapport | `frontend/docs/ops/email-production-readiness.md` |
| Index | `frontend/docs/ops/README.md` |

Code métier / ComptaPilot / SalesPilot / Home / Launcher / Command Center / Theme / Shell : **non modifié**.
