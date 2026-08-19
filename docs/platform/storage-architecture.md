# Architecture Storage ELFIS Core (RC2.4 étape 1)

## Objectif

Abstraction centrale des fichiers physiques et du registre documentaire logique.
Cette étape **ne remplace pas** les uploads ComptaPilot (`/api/documents`), Vault Supabase, ni l’OCR/IA legacy.
Les artefacts OCR RC2.5.3 utilisent le namespace `processing-artifacts` (privé), distinct des documents utilisateur.

## Vocabulaire

| Concept | Modèle | Rôle |
|---------|--------|------|
| **StorageObject** | `ElfisStorageObject` | Fichier physique chez un provider (`local` aujourd’hui) |
| **DocumentRecord** | `ElfisDocumentRecord` | Document logique ELFIS (métadonnées métier) |
| **DocumentLink** | `ElfisDocumentLink` | Lien document ↔ entité métier (`invoice`, `job`, …) |

Aucun modèle nommé simplement `Document` (collision avec ComptaPilot / Vault / DI).

## Providers

- Interface : `app/storage/storage_provider.py` (`StorageProvider`)
- `local` — disque local, UUID comme clé physique, écriture atomique
- `disabled` — refus explicite (sûr pour tests / prod non configurée)

Providers distants (S3, Supabase Storage) **non activés** sans configuration dédiée future.

## Configuration

| Variable | Défaut | Description |
|----------|--------|-------------|
| `STORAGE_PROVIDER` | `local` | `local` \| `disabled` |
| `STORAGE_LOCAL_ROOT` | `{storage_dir}/elfis_objects` | Racine locale |
| `STORAGE_MAX_FILE_SIZE_BYTES` | 15 Mo | Limite taille |
| `STORAGE_ALLOWED_MIME_TYPES` | pdf/png/jpeg/txt/json/csv | Allowlist |
| `STORAGE_BLOCKED_EXTENSIONS` | exe, bat, sh, … | Blocklist |
| `STORAGE_CHECKSUM_ENABLED` | `true` | SHA-256 |
| `STORAGE_QUARANTINE_ENABLED` | `false` | Quarantaine MIME |

## Sécurité

- Pas de confiance au `Content-Type` navigateur
- Protection path traversal
- Noms utilisateur jamais utilisés comme chemin définitif
- Pas de chemin physique exposé aux APIs / audits
- Pas de binaire volumineux en PostgreSQL

Voir [file-upload-security.md](../security/file-upload-security.md).

## System Health

Service id `storage` — provider réel `StorageHealthProvider` activable via :

- `SYSTEM_HEALTH_STORAGE_PROVIDER=real`
- ou `SYSTEM_HEALTH_USE_REAL_PROVIDERS=true`

Défaut : **mock**.

## Migration future

1. Brancher les uploads ComptaPilot / exports / emails sur `StorageService` (streaming)
2. Provider Supabase Storage ou S3 derrière le même contrat
3. Versions de document (`DocumentVersion`)
4. OCR / IA sur `DocumentRecord` (sans stocker le texte dans l’audit)

## RC2.4 étape 2 (ajout)

- Upload streaming (`StreamingUploadPipeline`) — pas de `file.read()` complet
- Compensation DB↔objet + quarantaine logique
- `DocumentAccessPolicy` + download/content sécurisés
- CLI `cleanup_temp` / `find_orphans`
- UI minimale `/elfadmin/documents`

## RC2.4 étape 4 (ajout)

- Provider `supabase` (`SupabaseStorageProvider`) + capacités
- Upload : streaming → tempfile OS → put distant
- Download proxy ELFIS (signed URL préparée)
- Migration progressive CLI + `elfis_storage_migrations`
- Intégrité CLI, admin read-only `/api/admin/storage/*`
- Voir [supabase-storage-provider.md](supabase-storage-provider.md)
