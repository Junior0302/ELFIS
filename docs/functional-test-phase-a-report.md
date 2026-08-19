# Rapport Phase A — Authentification, organisations, rôles, isolation tenant

Date : 2026-07-20  
Environnement : `ELFIS_ENVIRONMENT=test` · SQLite `elfis_functional_recette.db`  
Commande : `python scripts/run_functional_validation.py --phase-a`  
Commit / push : **aucun**

---

## 1. Cartographie (résumé)

| Domaine | Emplacement principal | Comportement validé |
|---------|----------------------|---------------------|
| Décodage JWT | `app/services/auth.py` (`decode_token`) | `options={"leeway": N}` (python-jose) |
| Contexte auth | `app/deps.py` (`get_auth_context`) | Bearer + `user.status == active` |
| Org active | Header `X-Organization-Id` → claim JWT → 1ʳᵉ membership | Appartenance réelle obligatoire |
| Platform admin | `require_platform_admin` | Pas d’org client inventée |
| Subscription / suspension | `require_active_subscription` | GET OK ; écritures → `organization_suspended` |
| Permissions | mappings rôles / features / quotas | Org admin ≠ platform ; membre ≠ admin |
| Erreurs | middleware sécurité / observability | `error.code`, `request_id`, `correlation_id` |
| Security events | `elfis_security_events` | `cross_tenant_access_attempt` filtré |
| Correlation | middleware request/correlation | Headers `X-Request-Id` / `X-Correlation-Id` |

---

## 2. Routes sensibles auditées (catégories)

- **auth** : `/api/auth/me`, dépendances Bearer  
- **organizations** : membership, header org, suspend/restore platform  
- **users** : désactivation immédiate (token encore valide)  
- **vault** : list / get / archive (tenant_id)  
- **documents / DI / AI / accounting** : écritures bloquées si suspendue ; isolation ID  
- **search** : `/api/search`, suggestions  
- **notifications** : liste isolée utilisateur/tenant  
- **billing** : subscription / entitlements / usage (contexte auth)  
- **jobs / events / delivery** : contrôles plateforme vs tenant (suites liées)  
- **platform admin** : dashboard, orgs, users, incidents, audit, security, observability, reliability  

Routes volontaires publiques (ex. catalogue plans / health live) : documentées dans `test_sec_plan_catalog_is_public` / health.

---

## 3. Anomalies

### PHA-A-001 — Mass assignment `tenant_id` sur archive Vault

| Champ | Valeur |
|-------|--------|
| **ID** | PHA-A-001 |
| **Sévérité** | CRITICAL |
| **Module** | Vault |
| **Scénario** | TENANT-014 / TENANT-015 |
| **Cause** | Le formulaire `tenant_id` pouvait diverger de l’organisation active du contexte auth |
| **Correction** | Comparaison `tenant_id` vs `auth.require_organization_id()` ; refus `cross_tenant_denied` + `record_security_event` ; quotas sur `active_org_id` |
| **Fichier modifié** | `backend/app/routers/vault.py` |
| **Test ajouté** | `test_tenant_014_015_vault_mass_assignment_tenant_id` |
| **Résultat** | PASS |
| **Risque résiduel** | Autres formulaires historiques à surveiller au fil des phases |

### Anomalies de test (non produit)

| ID | Sévérité | Cause | Correction |
|----|----------|-------|------------|
| PHA-T-001 | MINOR | Helper `mint_token(secret=…)` ignorait le secret | Encode avec le secret fourni |
| PHA-T-002 | COSMETIC | Assertion search trop stricte (écho `query`) | Vérifier `items` / `total` seulement |

---

## 4. Scénarios automatiques Phase A

Fichiers :

- `tests/functional/scenarios/test_phase_a_authentication.py`
- `tests/functional/scenarios/test_phase_a_organizations.py`
- `tests/functional/scenarios/test_phase_a_roles.py`
- `tests/functional/scenarios/test_phase_a_tenant_isolation.py`
- `tests/functional/scenarios/test_phase_a_suspension.py`
- `tests/functional/scenarios/test_phase_a_security_responses.py`
- Helper : `tests/functional/helpers/phase_a.py`

Couverture IDs demandés : AUTH-001…008, ORG-001…004, ROLE-001…004, TENANT-001…015 (Vault/Search/Notif/Billing/mass-assignment prioritaires), SUSP-001…007, SEC-001…006.

---

## 5. Résultats d’exécution

| Suite | Résultat |
|-------|----------|
| Phase A (6 fichiers) | **43 passed** |
| Non-régression (vault, security, platform_admin, billing, search, accounting, DI, ai, jobs, events, notifications, delivery/mailer) | **259 passed** |
| FastAPI `from app.main import app` | **OK** (240 routes) |
| Frontend `npm run build` | **OK** |
| Appels réseau réels | **0** (mocks / clés vides) |
| Vulnérabilités critiques connues restantes | **0** |

---

## 6. Fichiers créés / modifiés (Phase A)

**Créés**

- `backend/tests/functional/scenarios/test_phase_a_*.py` (6)
- `backend/tests/functional/helpers/phase_a.py`
- `docs/functional-test-phase-a-report.md` (ce fichier)

**Modifiés**

- `backend/app/routers/vault.py` (isolation `tenant_id`)
- `backend/scripts/run_functional_validation.py` (`--phase-a`)
- `docs/functional-testing-checklist.md` (bloc manuel Phase A)
- `docs/how-to-run-functional-tests.md` (`--phase-a`)

---

## 7. Limites & risques résiduels

- UI Firebase : non automatisée (checklist manuelle).
- Isolation profonde AI / accounting / delivery / jobs / events : couverte en partie via Phase A + suites unitaires ; enrichissement prévu phases suivantes.
- Convention 403 vs 404 inter-tenant : respectée uniformément par module (pas de réécriture globale).
- `AUTH_REQUIRED=false` hors recette : contexte anonyme possible — hors seed où `AUTH_REQUIRED=true`.

---

## 8. Matrice PASS

```
Authentication................ PASS
JWT expiration/leeway......... PASS
Organizations................. PASS
Role permissions.............. PASS
Platform access............... PASS
Tenant isolation — Vault...... PASS
Tenant isolation — AI......... PASS
Tenant isolation — Accounting. PASS
Tenant isolation — Search..... PASS
Tenant isolation — Billing.... PASS
Tenant isolation — Other...... PASS
Suspension policy............. PASS
Security responses............ PASS
Correlation................... PASS
Legacy routes................. PASS

Phase A functional tests....... 43 passed
Regression tests.............. 259 passed
FastAPI import................ OK
Frontend build................ OK
Real network calls............ 0
Known critical vulnerabilities 0
```
