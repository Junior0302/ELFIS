# Sécurité des uploads fichiers (RC2.4)

## Principes

1. Ne jamais faire confiance au `Content-Type` client
2. Ne jamais utiliser le nom original comme chemin de stockage
3. Ne jamais exposer le chemin physique
4. Ne jamais journaliser / auditer le contenu binaire
5. Refuser exécutables, scripts et doubles extensions dangereuses

## Contrôles (`storage_security.py`)

- Taille max (`STORAGE_MAX_FILE_SIZE_BYTES`)
- Fichier vide refusé
- Basename sanitisé (pas de `..`, caractères de contrôle)
- Extensions bloquées (exe, bat, sh, php, svg, …)
- Allowlist MIME (déclaré + détection magique partielle)
- Checksum SHA-256 optionnel
- Statut `quarantined` préparé (`STORAGE_QUARANTINE_ENABLED`)

## Provider local

- Racine configurable, résolution `Path.resolve()` + `relative_to`
- Clé = UUID + extension
- Écriture atomique (`mkstemp` + `os.replace`)
- Permissions fichier ~0644

## RC2.4 étape 2

- Lecture par chunks + limite runtime (`STORAGE_UPLOAD_CHUNK_SIZE_BYTES`)
- Codes stables : `FILE_TOO_LARGE`, `EMPTY_FILE`, `BLOCKED_EXTENSION`, `MIME_MISMATCH`, `INVALID_FILENAME`, `UNSUPPORTED_TYPE`, `SECURITY_POLICY_REJECTED`, `UPLOAD_INTERRUPTED`
- Détection MZ / archives / doubles extensions
- Quarantaine : `STORAGE_QUARANTINE_ENABLED` + namespace `STORAGE_QUARANTINE_NAMESPACE`
- Metadata JSON sanitisée (secrets / profondeur / taille)

## Hors scope

- Antivirus externe
- OCR / analyse IA
- Provider distant (S3 / Supabase) en production
