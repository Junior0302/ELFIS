# 04 — Modèle rôles globaux ELFIS

## Rôles visibles (UI)

| Rôle | Description courte |
|------|-------------------|
| Propriétaire | Contrôle complet ; protégé |
| Administrateur | Membres, rôles, paramètres, sécurité, abonnements |
| Gestionnaire | Opérationnel étendu sans contrôle org complet |
| Collaborateur | Espaces attribués ; CRUD selon permissions |
| Lecteur | Consultation seule |

## Mapping affichage (clés backend inchangées)

| Clé backend | Libellé UI |
|-------------|------------|
| `owner` | Propriétaire |
| `admin` | Administrateur |
| `cfo` | Gestionnaire |
| `comptable` | Collaborateur |
| `employe` | Collaborateur |
| `auditeur` | Lecteur |

Invitation : options dédupliquées — Gestionnaire→`cfo`, Collaborateur→`employe`, Lecteur→`auditeur`.

Permissions / enums / tables : **non migrés** dans cette phase.

Module : `frontend/src/platform-roles/globalRoles.ts`  
Miroir libellés API : `backend/app/services/plan_features.py` (`ROLE_LABELS_FR`).
