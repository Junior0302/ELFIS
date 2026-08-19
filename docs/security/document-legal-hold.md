# Legal hold documentaire — RC2.4 étape 3

## Modèle

`ElfisDocumentLegalHold` : raison obligatoire, référence optionnelle, `active`, acteurs pose/levée.

## Permissions

- `documents.legal_hold.read`
- `documents.legal_hold.manage`

`storage.objects.purge` et `documents.retention.manage` restent réservés (super_admin).  
Un platform admin **sans** permission explicite ne contourne pas le hold pour purger.

## Règles

- Document sous hold actif : purge physique interdite (versions + storage objects associés)
- Archivage logique autorisé
- Aucune levée automatique
- Double release idempotente
- Isolation tenant stricte

## Audit

- `DOCUMENT_LEGAL_HOLD_PLACED`
- `DOCUMENT_LEGAL_HOLD_RELEASED`
- `DOCUMENT_PURGE_BLOCKED` (si tentative pendant hold)

Métadonnées limitées (ids, raison tronquée) — jamais de contenu ni chemin.
