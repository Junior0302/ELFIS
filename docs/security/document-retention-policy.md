# Politique de rétention documentaire — RC2.4 étape 3

## Configuration

| Setting | Rôle |
|---------|------|
| `DOCUMENT_RETENTION_DEFAULT_DAYS` | Rétention par défaut |
| `DOCUMENT_RETENTION_DELETED_GRACE_DAYS` | Grâce après soft-delete |
| `DOCUMENT_RETENTION_ARCHIVED_DAYS` | Base archivée |
| `DOCUMENT_RETENTION_SECURITY_MIN_DAYS` | Plancher sécurité |
| `DOCUMENT_PURGE_BATCH_SIZE` | Taille de lot purge |

## Règles

- Type `invoice` / `quote` / `export` → rétention allongée
- Statut `archived` / `deleted` → bases et délais dédiés
- Legal hold actif → **jamais** éligible à la purge
- Lien métier bloquant (`invoice`, `quote`, `attachment`, …) → purge refusée (pas de cascade)

`DocumentRetentionService.explain_retention_decision` expose règle, échéance, blocage.

## Soft-delete / restore

API : `POST /api/document-registry/{id}/delete` et `/restore`  
Permissions : `documents.delete`, `documents.restore`  
Les objets physiques et versions sont conservés jusqu’à purge CLI.

## Purge physique

**CLI uniquement** — aucune route publique, aucun bouton UI, aucune purge au démarrage.

```bash
python -m scripts.storage.retention --preview
python -m scripts.storage.retention --purge --before YYYY-MM-DD --batch-size 100 --confirm
# production : --confirm-production obligatoire
```

Ordre : candidats → re-vérif hold/liens → **purge artefacts extraction** → **purge artefacts OCR** → delete physique → mark DB → tombstone.  
Préférer un orphelin / reprise idempotente plutôt qu’une perte silencieuse de contenu.

Les artefacts OCR et extraction (`processing-artifacts`) sont purgés avec le document ; le tombstone ne conserve **jamais** le texte OCR ni les valeurs extraites.

## Tombstones

`elfis_document_tombstones` : métadonnées minimales (ids, dates, checksum tronqué, raison).  
Pas de contenu, chemin, URL ni secrets.
