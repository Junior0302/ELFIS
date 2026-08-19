# Supabase Storage Provider — RC2.4 étape 4

## Choix technique

- **HTTP httpx** (comme le client Vault), pas le SDK lourd
- Client injectable : `SupabaseStorageHttpClient` / `SupabaseStorageClientFactory`
- Upload : streaming client → **tempfile OS** → `put_stream` distant
- Download défaut : **proxy ELFIS** (`open_stream` + `StreamingResponse`)
- URL signées : préparées (`create_signed_download_url`) mais **non utilisées** par défaut

## Capacités

| Capacité | Local | Supabase |
|----------|-------|----------|
| atomic move | oui | non |
| signed URLs | non | oui |
| prefers local temp then remote put | non | oui |

## Configuration

Réutilise `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` si les variables `SUPABASE_STORAGE_*` sont vides.

Variables dédiées : bucket, namespaces, timeout, retries, TTL signed URL.

`STORAGE_PROVIDER=local|supabase|disabled` — défaut tests : `local`.

## Clés

`documents/{org_id}/{yyyy}/{mm}/{uuid}` — jamais filename / email / PII.

## Sécurité

- Bucket privé
- Service role serveur uniquement
- Aucun secret dans logs / audit / frontend
- Compensation si DB échoue après upload distant
