# 08 — Frontières de sécurité

**P3.0** · Droits, audit, validation humaine, rollback.

---

## Principe absolu

```
Les workflows ne contournent JAMAIS les droits utilisateur.
```

L’Orchestrator peut **proposer** et **enchaîner** ; seul le Pilot (et Core pour l’ACL plateforme) **autorise** l’exécution.

---

## Responsabilités

| Acteur | Responsable de | Non responsable de |
|--------|----------------|--------------------|
| **Utilisateur** | Consentir / valider gates | Contourner ACL |
| **Command Center** | Transmettre l’acteur réel | Élever les privilèges |
| **Orchestrator** | Vérifier préconditions, journaliser, stopper si denied | Posséder une « backdoor » métier |
| **Pilot** | AuthZ fine + validation métier | Faire confiance aveugle à l’Orchestrator |
| **Core** | Identité, org, rôles plateforme | Règles TVA / CRM |
| **Audit** | Immutabilité des traces | Décider du métier |

```
Actor token / session
        │
        ▼
Orchestrator (ne forge pas d’identité)
        │  forward actor + org
        ▼
Pilot AuthZ ──denied──► stop workflow + audit
        │ allow
        ▼
Execute
```

---

## Permissions

| Règle | Détail |
|-------|--------|
| Périmètre org | Tout event / action est scopé `orgId` |
| Permission par action | Table Pilot (voir 05) |
| Moindre privilège | Le workflow n’utilise que les droits de l’acteur (sauf service account documenté) |
| Service accounts | Exception rare, audité, scope minimal, jamais pour « tout faire » |
| Élévation | Interdite via Orchestrator |

Si l’étape N est `denied`, le workflow passe en `failed` ou `partial` selon criticité — **pas** d’essai avec un autre utilisateur.

---

## Audit & traçabilité

Chaque enchaînement conserve conceptuellement :

| Élément | Usage |
|---------|--------|
| `correlationId` | Relie CC → workflow → events |
| `actorId` | Qui a initié |
| `orgId` | Où |
| Timeline des étapes | Qui a accepté / refusé / échoué |
| Event ids | Preuves des faits |

```
CC cmd ──corr──► Workflow run
                    ├─ step Compta (ok)
                    ├─ step Doc (denied) ──► audit + stop/partial
                    └─ events émis liés
```

Consultation audit : réservée aux rôles admin / compliance selon politique org.

---

## Validation humaine (gates)

Obligatoire (exemples conceptuels) :

| Situation | Gate |
|-----------|------|
| Impact financier élevé | Validation manager / comptable |
| Classification Doc faible confiance | Revue humaine |
| Offboarding / user.removed | Confirmation admin |
| Automation destructive | Double confirmation |

```
… → step → [ awaiting_validation ] → humain ✓/✗ → suite / cancel
```

Une automation **ne valide pas à la place** de l’humain quand le gate est requis.

---

## Rollback & compensation

| Niveau | Comportement |
|--------|--------------|
| Avant commit Pilot | Annulation simple |
| Après succès partiel | Compensation : actions inverses **si le Pilot les expose** |
| Impossible à inverser | Marquer `failed`, alerter, correction manuelle |

```
A ok → B ok → C fail
         │
         ▼
 compenser B? → compenser A? → audit + Notify admin
```

Pas de « delete everywhere » silencieux.

---

## Isolation & données

- Pas de fuite cross-org via events.  
- Payloads minimaux (IDs).  
- Secrets hors events.  
- Listeners reçoivent seulement ce que leur rôle justifie (filtrage conceptuel).

---

## Checklist sécurité workflow

- [ ] Acteur authentifié et org active  
- [ ] Chaque étape mappe une permission Pilot  
- [ ] Denied → stop / partial documenté  
- [ ] Gate humaine si risque  
- [ ] correlationId présent  
- [ ] Compensation ou procédure manuelle définie  
- [ ] Aucune élévation de privilège  

Si un item échoue → **ne pas démarrer** ou **ne pas continuer**.
