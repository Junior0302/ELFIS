# Checklist manuelle — Recette ELFIS Core / ComptaPilot IA

Mot de passe seed : `ElfisRecette!Test-2026` (API : JWT ; UI : Firebase test).

Légende statut : `PASS` | `FAIL` | `BLOCKED` | `N/A`

---

## PHASE A — Manuel UI (auth / orgs / rôles / isolation)

Prérequis : seed chargé ; API port 8000 ; frontend 5173 ; comptes Firebase de test mappés aux e-mails seed.  
Firebase réel non automatisé dans cette phase.

| # | Scénario | Compte | Résultat attendu | Statut | Preuve / notes |
|---|----------|--------|------------------|--------|----------------|
| A-UI-01 | Connexion Firebase admin org | `org.admin@…` | Session OK | | |
| A-UI-02 | Affichage organisation | idem | ORG_ACTIVE visible | | |
| A-UI-03 | Navigation pages autorisées | idem | Dashboard, Vault, Billing, etc. | | |
| A-UI-04 | Absence menu plateforme | idem | Pas d’entrée `/elfadmin` | | |
| A-UI-05 | Connexion membre | `member@…` | Session OK | | |
| A-UI-06 | Boutons admin absents/désactivés | `member@…` | Pas gestion users / abo / validation réservée | | |
| A-UI-07 | URL interdite directe | `member@…` | Message d’erreur propre / redirection | | |
| A-UI-08 | Message d’erreur lisible | tout | Pas de stack / secret | | |
| A-UI-09 | Connexion platform admin | `platform.admin@…` | Session OK | | |
| A-UI-10 | Accès `/elfadmin` | platform | Dashboard plateforme | | |
| A-UI-11 | Fiche organisation | platform | Détail ORG_* | | |
| A-UI-12 | Suspension org | platform | Raison obligatoire ; audit | | |
| A-UI-13 | Comportement utilisateur suspendu | `suspended@…` | Lecture OK ; écritures refusées | | |
| A-UI-14 | Restauration | platform | Remettre ORG_SUSPENDED ensuite | | |
| A-UI-15 | ID autre tenant dans l’URL | `other.tenant@…` | 403/404 UI propre | | |
| A-UI-16 | Déconnexion / purge session | tout | Token local vidé | | |
| A-UI-17 | Expiration session | JWT court / attente | Retour login | | |
| A-UI-18 | Rafraîchissement page | connecté | Session conservée ou re-login propre | | |
| A-UI-19 | Deux onglets | connecté | Comportement cohérent | | |
| A-UI-20 | Responsive minimum | mobile | Nav et formulaires utilisables | | |

Actions manuelles restantes (hors auto Phase A) : Firebase Auth réel, parcours UI complet ci-dessus, pentest offensif, perf.

---

## PHASE B — Manuel UI (Billing / essai / quotas)

Prérequis : seed ; API 8000 ; frontend ; **aucun** appel Stripe réel (mocks / clés vides).  
Checkout Stripe Test réel = scénario futur documenté seulement.

| # | Scénario | Compte | Résultat attendu | Statut | Notes |
|---|----------|--------|------------------|--------|-------|
| B-UI-01 | Page plans | `nosub@` / public | Starter 19 €, 14 j visibles | | |
| B-UI-02 | Essai actif | `trial@` | Status trialing | | |
| B-UI-03 | Message 14 j puis 19 €/mois | `trial@` | Texte disclosure | | |
| B-UI-04 | Renouvellement automatique | `trial@` / `active@` | will_renew visible | | |
| B-UI-05 | Quota proche | `quota.near@` | ~80 % | | |
| B-UI-06 | Quota atteint | `quota.full@` + enforce | Blocage upload | | |
| B-UI-07 | Checkout Stripe Test (futur) | `nosub@` | URL session | BLOCKED si pas Stripe Test |
| B-UI-08 | Retour checkout | — | Statut mis à jour | | |
| B-UI-09 | Abonnement actif | `active@` | Actif 19 € | | |
| B-UI-10 | Customer portal | `active@` | Ouverture portail | | |
| B-UI-11 | Cancel | `active@` / `cancelled@` | cancel_at_period_end | | |
| B-UI-12 | Resume | `cancelled@` | Portail / reprise | | |
| B-UI-13 | Payment failed simulé | webhook mock | past_due | API auto |
| B-UI-14 | Grâce | `pastdue@` | Lecture OK, écriture limitée | | |
| B-UI-15 | Expiration grâce | `pastdue.expired@` | Coûteux bloqué | | |
| B-UI-16 | Consultation après expiration | `expired@` | Données visibles | | |
| B-UI-17 | Org suspendue + billing | `suspended@` | Billing consultable / écritures métier non | | |
| B-UI-18 | Org admin vs membre | `org.admin` / `member` | Membre sans manage | | |
| B-UI-19 | Double clic checkout | admin | Pas de double session abusive | | |
| B-UI-20 | Responsive /abonnement | mobile | OK | | |

Rapport auto : `docs/functional-test-phase-b-report.md`  
Commande : `python scripts/run_functional_validation.py --reset-db --phase-b`

---

## PHASE C — Manuel UI (Documents / Vault / IA / Comptabilité)

Prérequis : seed ; API 8000 ; frontend ; **OpenAI/OCR/storage externes off** (mocks).  
Rapport auto : `docs/functional-test-phase-c-report.md`  
Commande : `python scripts/run_functional_validation.py --reset-db --phase-c`

| # | Scénario | Compte | Résultat attendu | Statut | Notes |
|---|----------|--------|------------------|--------|-------|
| C-UI-01 | Déposer facture fournisseur | `active@` | Archive OK | | |
| C-UI-02 | Voir progression | idem | Jobs / statut | | |
| C-UI-03 | Résultat extraction | idem | Texte / métadonnées | | |
| C-UI-04 | Données IA | idem | Classification | | |
| C-UI-05 | Proposition comptable | idem | Lignes visibles | | |
| C-UI-06 | Équilibre | idem | Débit = crédit | | |
| C-UI-07 | Valider | `org.admin@` | Validated | | |
| C-UI-08 | Rejeter | admin | Raison obligatoire | | |
| C-UI-09 | Facture incohérente | active | requires_review | | |
| C-UI-10 | Faible confiance | active | Revue | | |
| C-UI-11 | Scan OCR requis | active | awaiting_ocr / message | | |
| C-UI-12 | Fichier corrompu | active | Erreur propre | | |
| C-UI-13 | Double upload | active | 409 doublon | | |
| C-UI-14 | Quota atteint | `quota.full@` | Refus | | |
| C-UI-15 | Abo bloqué | `nosub@` / expired | Refus coûteux | | |
| C-UI-16 | Org suspendue | `suspended@` | Upload refusé | | |
| C-UI-17 | Retry admin | platform | Job retry | | |
| C-UI-18 | Notification | active | Visible | | |
| C-UI-19 | Recherche | active | Fournisseur trouvé | | |
| C-UI-20 | Responsive | mobile | OK | | |
| C-UI-21 | Loader | — | Pendant traitement | | |
| C-UI-22 | Erreur propre | — | Pas de stack | | |
| C-UI-23 | Refresh pendant traitement | — | Cohérent | | |
| C-UI-24 | Deux onglets | — | Cohérent | | |
| C-UI-25 | Navigation après validation | — | Lecture seule | | |

---

## PHASE D — Manuel UI (Validation / Delivery / Notifs / Search)

Prérequis : seed ; API 8000 ; frontend ; **aucun e-mail réel** (mock Brevo/`httpx`) ; stockage Vault mock.  
Rapport auto : `docs/functional-test-phase-d-report.md`  
Commande : `python scripts/run_functional_validation.py --reset-db --phase-d`

| # | Scénario | Compte | Résultat attendu | Statut | Notes |
|---|----------|--------|------------------|--------|-------|
| D-UI-01 | Ouvrir proposition | `org.admin@` | Détail + lignes | | |
| D-UI-02 | Valider proposition équilibrée | admin | status validated | | |
| D-UI-03 | Rejeter avec raison | admin | rejected + historique | | |
| D-UI-04 | Voir historique comptable | admin | actions datées | | |
| D-UI-05 | Ouvrir facture | admin | métadonnées + PDF | | |
| D-UI-06 | Cliquer envoyer | admin | formulaire prérempli | | |
| D-UI-07 | Destinataire prérempli | — | e-mail client | | |
| D-UI-08 | Sujet prérempli | — | numéro facture | | |
| D-UI-09 | Corps prérempli | — | modèle | | |
| D-UI-10 | Pièce jointe automatique | — | PDF joint, pas de re-upload | | |
| D-UI-11 | Expéditeur personnel | admin | option visible / reply-to | | |
| D-UI-12 | Adresse ELFIS active | si active | sélectionnable | | |
| D-UI-13 | Adresse ELFIS pending | après demande | non utilisable | | |
| D-UI-14 | Envoi réussi | admin | sent + notif | | |
| D-UI-15 | Envoi échoué | mock fail | email_failed compréhensible | | |
| D-UI-16 | Retry manuel | admin | succès sans double blob | | |
| D-UI-17 | Double clic envoyer | admin | already_sent / 1 e-mail | | |
| D-UI-18 | Notification | admin | validation / envoi | | |
| D-UI-19 | Historique d’envoi | admin | statut + tentatives | | |
| D-UI-20 | Recherche facture | admin | numéro trouvé | | |
| D-UI-21 | Recherche devis | admin | trouvé | | |
| D-UI-22 | Statut Search à jour | après validate | validated | | |
| D-UI-23 | Quota e-mail atteint | override | 429 | | |
| D-UI-24 | Org suspendue | `suspended@` | envoi bloqué | | |
| D-UI-25 | Membre simple | `member@` | validate refusé | | |
| D-UI-26 | Autre tenant par URL | `other.tenant@` | 403/404 | | |
| D-UI-27 | Loader | — | pendant envoi | | |
| D-UI-28 | Message d’erreur | — | pas de stack / clé | | |
| D-UI-29 | Responsive | mobile | OK | | |
| D-UI-30 | Deux onglets | — | pas de double envoi | | |

---

## PHASE E — Manuel UI (Platform Admin / Ops / Fiabilité)

Prérequis : compte `platform.admin@test.elfis.local` ; API 8000 ; frontend ; **aucun appel réseau réel**.  
Rapport auto : `docs/functional-test-phase-e-report.md`  
Commande : `python scripts/run_functional_validation.py --reset-db --phase-e`

| # | Scénario | Compte | Résultat attendu | Statut | Notes |
|---|----------|--------|------------------|--------|-------|
| E-UI-01 | Ouvrir `/elfadmin` | platform_admin | Dashboard | | |
| E-UI-02 | Dashboard | admin | Agrégats visibles | | |
| E-UI-03 | Filtres période 24h/7d/30d | admin | Cohérent | | |
| E-UI-04 | Liste organisations | admin | Seed visible | | |
| E-UI-05 | Fiche organisation | admin | Ops detail | | |
| E-UI-06 | Suspendre org | admin | Raison obligatoire | | |
| E-UI-07 | Vérifier côté utilisateur | suspended | Écritures bloquées | | |
| E-UI-08 | Restaurer org | admin | Accès rétabli | | |
| E-UI-09 | Liste utilisateurs | admin | Sans secrets | | |
| E-UI-10 | Désactiver utilisateur | admin | status suspended | | |
| E-UI-11 | Session bloquée | member désactivé | 401 | | |
| E-UI-12 | Réactiver | admin | Accès OK | | |
| E-UI-13 | Abonnements | admin | Liste filtrée | | |
| E-UI-14 | Quotas | admin | Lecture | | |
| E-UI-15 | Entitlements | admin | Override éventuel | | |
| E-UI-16 | Documents | admin | Pas de PDF | | |
| E-UI-17 | Jobs | admin | Liste | | |
| E-UI-18 | Retry job | admin | Raison + audit | | |
| E-UI-19 | Cancel job | admin | canceled | | |
| E-UI-20 | Events | admin | Liste | | |
| E-UI-21 | Retry event | admin | pending | | |
| E-UI-22 | Resolve event | admin | processed | | |
| E-UI-23 | Incidents | admin | Liste | | |
| E-UI-24 | Acknowledge | admin | acknowledged | | |
| E-UI-25 | Resolve incident | admin | resolved | | |
| E-UI-26 | Audit | admin | Actions sensibles | | |
| E-UI-27 | Security | admin | Events filtrés | | |
| E-UI-28 | Observability | admin | Metrics | | |
| E-UI-29 | Reliability | admin | Dry-run | | |
| E-UI-30 | Health | public/admin | live/ready/details | | |
| E-UI-31 | Pagination | admin | Bornée | | |
| E-UI-32 | Filtres | admin | OK | | |
| E-UI-33 | Erreurs | admin | Sans stack | | |
| E-UI-34 | Confirmations | admin | UI | | |
| E-UI-35 | Raisons obligatoires | admin | 422 si courte | | |
| E-UI-36 | Responsive | mobile | OK | | |
| E-UI-37 | Deux onglets | admin | Cohérent | | |
| E-UI-38 | Rafraîchissement | admin | Cohérent | | |
| E-UI-39 | Accès org admin refusé | org_admin | 403 | | |
| E-UI-40 | Déconnexion | admin | Session fermée | | |

---

## PHASE F — Performance / Concurrence (manuel + mesures)

Prérequis : mocks ; **pas d’URL production** ; SQLite = indicatif ; Postgres = `ELFIS_PERFORMANCE_DATABASE_URL`.  
Rapports : `docs/functional-test-phase-f-report.md`, `docs/performance-baseline.md`  
Commande rapide : `python scripts/run_functional_validation.py --reset-db --phase-f`  
Concurrence Postgres : `python scripts/performance/run_phase_f.py --postgres`

| # | Scénario | Environnement | Résultat attendu | Statut | Notes |
|---|----------|---------------|------------------|--------|-------|
| F-UI-01 | Health p95 | local | < 2s indicatif | | |
| F-UI-02 | Liste documents paginée | local | Bornée | | |
| F-UI-03 | Search | local | Tenant filtré SQL | | |
| F-UI-04 | Dashboard 24h/7d/30d | local | Pas de N+1 | | |
| F-UI-05 | Double validation proposition | local | 1 écriture | | |
| F-UI-06 | Double envoi même clé | local | 1 mail mock | | |
| F-UI-07 | Quota restant 1 | local/PG | 1 OK / refus | | |
| F-UI-08 | Jobs 2 workers | local/PG | Pas de double claim | | |
| F-UI-09 | Events 2 workers | local/PG | Pas de double claim | | |
| F-UI-10 | Upload doublon hash | local | 409/reuse | | |
| F-UI-11 | Isolation Search 2 tenants | local | Aucune fuite | | |
| F-UI-12 | Webhook event_id double | local | 1 ligne | | |
| F-UI-13 | Stale job | local | Incident dédupliqué | | |
| F-UI-14 | Script refuse prod URL | — | RuntimeError | | |
| F-UI-15 | SKIP LOCKED | Postgres | Documenté | | |

---

## Authentification

### FUNC-AUTH-001
- **Préconditions** : seed chargé
- **Compte** : `org.admin@test.elfis.local`
- **Étapes** : obtenir session (Firebase UI ou JWT API) ; appeler `/api/auth/me`
- **Résultat attendu** : utilisateur actif, org ORG_ACTIVE
- **Résultat obtenu** :
- **Statut** :
- **Preuve** :
- **Anomalie** :

### FUNC-AUTH-002
- **Préconditions** : seed
- **Compte** : `other.tenant@test.elfis.local`
- **Étapes** : tenter d’accéder aux documents de ORG_ACTIVE via `X-Organization-Id`
- **Résultat attendu** : 403 / accès refusé
- **Résultat obtenu** :
- **Statut** :

---

## Organisations

### FUNC-ORG-001 — Suspendue
- **Compte** : `suspended@test.elfis.local`
- **Étapes** : lecture documents ; tentative upload
- **Résultat attendu** : lecture possible ; upload refusé (`organization_suspended`)
- **Statut** :

---

## Billing

### FUNC-BILL-001 — Essai
- **Compte** : `trial@test.elfis.local`
- **Étapes** : consulter statut abonnement
- **Résultat attendu** : `trialing`, dates d’essai futures, renouvellement auto prévu
- **Statut** :

### FUNC-BILL-002 — Actif 19 €
- **Compte** : `active@test.elfis.local`
- **Résultat attendu** : `active`, plan starter, prochaine échéance future
- **Statut** :

### FUNC-BILL-003 — Past due grâce
- **Compte** : `pastdue@test.elfis.local`
- **Résultat attendu** : `past_due`, lecture OK, écritures selon politique grâce
- **Statut** :

### FUNC-BILL-004 — Quota
- **Compte** : `quota.full@test.elfis.local` + `ELFIS_BILLING_ENFORCE_QUOTAS=true`
- **Étapes** : upload document
- **Résultat attendu** : `quota_exceeded` / 402-403
- **Statut** :

---

## Documents

### FUNC-DOC-001 — Facture fournisseur valide
- **Compte** : `active@test.elfis.local`
- **Étapes** : déposer `invoice_supplier_valid.pdf` ; attendre jobs ; ouvrir analyse / proposition
- **Résultat attendu** : archivé ; extraction ; analyse ; proposition ; notification
- **Statut** :

### FUNC-DOC-002 — Facture incohérente
- **Fichier** : `invoice_unbalanced.pdf`
- **Résultat attendu** : `requires_review` ; pas de validation auto
- **Statut** :

---

## IA / Comptabilité

### FUNC-ACC-001 — Validation humaine
- **Étapes** : ouvrir proposition ready ; valider ; vérifier historique ; tentative modification refusée
- **Statut** :

---

## E-mails / Delivery

### FUNC-DEL-001
- **Étapes** : envoyer facture/devis ; vérifier outbox mock (pas d’envoi réel)
- **Résultat attendu** : destinataire, sujet, PJ, statut sent
- **Statut** :

---

## Recherche / Notifications

### FUNC-SEA-001 / FUNC-NOT-001
- Recherche fournisseur ; notification visible ; isolation tenant
- **Statut** :

---

## Admin

### FUNC-ADM-001
- **Compte** : `platform.admin@test.elfis.local`
- **Étapes** : dashboard ; fiche org ; incidents ; retry job ; audit
- **Statut** :

---

## Sécurité / Observabilité / Fiabilité

### FUNC-SEC-001 — Request ID
- Headers `X-Request-Id` / `X-Correlation-Id` présents ; erreur normalisée
- **Statut** :

### FUNC-OBS-001 — Health
- `/api/health/live` OK ; `/api/health/ready` OK
- **Statut** :

### FUNC-REL-001 — Cleanup dry-run
- Admin Fiabilité → dry-run ; aucun document métier supprimé
- **Statut** :

---

## Mobile / Accessibilité / Erreurs

### FUNC-UX-001 — responsive pages clés
### FUNC-UX-002 — focus clavier formulaires auth
### FUNC-ERR-001 — retry job après erreur IA temporaire

---

## Matrice comptes rapides

| Email | Org | Scénario |
|-------|-----|----------|
| platform.admin@test.elfis.local | ORG_ACTIVE | Platform admin |
| org.admin@test.elfis.local | ORG_ACTIVE | Admin org |
| member@test.elfis.local | ORG_ACTIVE | Membre |
| trial@test.elfis.local | ORG_TRIAL | Essai |
| active@test.elfis.local | ORG_ACTIVE | Actif |
| pastdue@test.elfis.local | ORG_PAST_DUE | Past due |
| cancelled@test.elfis.local | ORG_CANCELLED | Cancel at period end |
| suspended@test.elfis.local | ORG_SUSPENDED | Suspendue |
| other.tenant@test.elfis.local | ORG_SECOND_TENANT | Isolation |
| nosub@test.elfis.local | ORG_NONE | Sans abo |
| quota.near@test.elfis.local | ORG_QUOTA_NEAR | Quota 80% |
| quota.full@test.elfis.local | ORG_QUOTA_FULL | Quota plein |

---

## PHASE G — Production readiness (manuel ops)

Prérequis : Phase A–F validées ; **aucun** appel Stripe/OpenAI/SMTP/Supabase réel pendant la suite auto.  
Rapport : `docs/functional-test-phase-g-report.md`  
Commande : `python scripts/run_functional_validation.py --phase-g`  
Checklists : `docs/deployment/production-checklist.md`, `docs/deployment/staging-checklist.md`  
Runbooks : `docs/runbooks/`

| # | Scénario | Résultat attendu | Statut | Notes |
|---|----------|------------------|--------|-------|
| G-01 | Configuration staging | Env/providers/secrets dédiés | | |
| G-02 | Configuration production | Refus SQLite/mocks/debug | | |
| G-03 | Secret manquant | Démarrage fatal explicite | | |
| G-04 | Debug activé | Refusé en prod | | |
| G-05 | Mock activé | Refusé en prod | | |
| G-06 | SQLite production | Refusé | | |
| G-07 | CORS invalide / `*` | Refusé avec credentials | | |
| G-08 | Démarrage API | OK si config valide | | |
| G-09 | Démarrage worker | OK ; pas d’appel réseau idle | | |
| G-10 | Arrêt API | SIGTERM gracieux | | |
| G-11 | Arrêt worker | Stop claim + grace | | |
| G-12 | Liveness | `/api/health/live` | | |
| G-13 | Readiness | `/api/health/ready` | | |
| G-14 | Provider degraded | ready degraded, pas forcément unready | | |
| G-15 | Migration base vide | SQL scripts OK (staging PG) | | |
| G-16 | Migration base existante | Données préservées | | |
| G-17 | Vérification index | Delivery / webhook / vault / GIN | | |
| G-18 | Sauvegarde | Runbook + checksum | | |
| G-19 | Checksum backup | `verify_backup.py` | | |
| G-20 | Restauration temporaire | Jamais prod directe | | |
| G-21 | Smoke staging | Non destructif | | |
| G-22 | Smoke prod read-only | `--allow-production-readonly` | | |
| G-23 | Rollback applicatif | Tag précédent | | |
| G-24 | Rotation JWT | Sessions invalidées contrôlées | | |
| G-25 | Rotation Stripe | Signature OK | | |
| G-26 | Rotation mailer | Staging only probe | | |
| G-27 | Incident worker | Runbook | | |
| G-28 | Incident storage | Runbook | | |
| G-29 | Incident AI | Kill-switch | | |
| G-30 | Incident Stripe | Idempotence | | |
| G-31 | Logs | Pas de secrets | | |
| G-32 | Métriques | Présentes / auth | | |
| G-33 | Alertes | Minimales documentées | | |
| G-34 | Compte test absent | Pas de seed prod | | |
| G-35 | Routes debug absentes | Prod | | |
| G-36 | OpenAPI | Désactivé prod | | |
| G-37 | CSP / headers | HSTS etc. | | |
| G-38 | Frontend prod | Build OK | | |
| G-39 | Variables frontend | Pas de secret serveur | | |
| G-40 | Décision go/no-go | Checklist production | | |
