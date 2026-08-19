# 11 — Supabase Vault upload remediation (A1.1.5)

## Verdict

**GO** — cause racine corrigée ; upload / signed URL / download / delete diagnostic OK sur bucket `elfis-vault` privé.

## Cause exacte

| Champ | Valeur |
|-------|--------|
| Cause | `SUPABASE_URL` malformée : schéma `https:HOST` **sans** `//` |
| Classification | `invalid_url` / `UnsupportedProtocol` (httpx) |
| HTTP status | *aucun* (échec transport avant requête réseau) |
| Message nettoyé | `UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol.` |
| Bucket attendu | `elfis-vault` |
| Log métier avant fix | `vault_storage_upload_error` (détails transport non capturés) |

### Causes A–G (checklist)

| Code | Cause | Résultat |
|------|-------|----------|
| A | Bucket manquant | **Non** — `elfis-vault` présent, `public=false` |
| B | Mauvaise clé | **Non** — JWT `role=service_role` |
| C | Mauvaise URL | **Oui** — `https:…supabase.co` au lieu de `https://…supabase.co` |
| D | Headers | N/A (requête jamais émise) ; headers client OK après fix |
| E | Object path | N/A ; chemins sans slash initial forcé côté client |
| F | Bucket privé + service_role | OK après fix URL |
| G | Taille / 413 | Non |

## Config vérifiée (runtime, sans secrets)

- `supabase_url_configured` = true
- `service_role_configured` = true
- `ELFIS_VAULT_BUCKET` = `elfis-vault`
- `url_scheme_https` = true (après fix)
- `url_has_storage_v1_suffix` = false (correct : le client ajoute `/storage/v1/...`)
- `key_length` = 219
- `masked_key_prefix` = `eyJhbGci...`

## Correctifs appliqués

1. **`.env`** — `SUPABASE_URL` normalisée `https://…` (valeurs non documentées ici).
2. **`app/config.py`** — `_normalize_http_base_url` : `https:host` → `https://host` (idem `http:`, guillemets, slash final). Appliqué à `supabase_url` et `supabase_storage_url`.
3. **`app/core/supabase_storage_client.py`** — erreurs typées `SupabaseStorageError` ; logs sûrs : `status_code`, `error_code`, `error_message`, `classification`, `endpoint` masqué (`https://HOST/...`), `bucket`, `path`, `content_type`, `content_size`, `timeout`. Jamais Authorization / apikey / PDF / service_role. Classification : `bucket_missing`, `authentication_failed`, `forbidden`, `invalid_url`, `timeout`, `project_unreachable`, `payload_too_large`, etc. Strip du slash initial sur les paths.
4. **`app/services/vault/storage_service.py`** — `vault_storage_upload_error` propage les métadonnées non secrètes.
5. **Script** — `backend/scripts/diagnose_vault_supabase_upload.py`.

**Non modifié (volontairement)** : flux métier `DocumentDeliveryService` / email ; pas de fallback local ; pas de second provider.

## Test isolé Storage

Commande : `python -m scripts.diagnose_vault_supabase_upload` (cwd `backend/`).

Résultat :

- list buckets OK — `elfis-vault` présent, privé
- upload `diagnostics/vault-test-{timestamp}.pdf` OK
- signed URL OK
- download bytes == upload OK
- delete diagnostic OK
- **status = GO**

## Chaîne email facturation

- Avant : `POST /api/billing/documents/{id}/email` → archivage Vault → `vault_storage_upload_error` → `archive_failed` → **HTTP 503**.
- Après fix URL : le prérequis Storage Vault fonctionne (prouvé par diagnostic GO).
- Test HTTP bout-en-bout email (Brevo/SMTP + destinataire test) : **non rejoué dans cette phase** (évite envoi client réel). Prérequis Storage pour l’archivage PDF est levé.

## Tests automatisés

`backend/tests/vault/test_supabase_vault_upload.py` :

- normalisation URL
- 404 bucket / 401 auth / 413 taille
- path sans double slash
- invalid_url transport
- signed URL + download mock
- mapping `VaultStorageError` sans fuite de secret

## GO / NO GO

| Critère | Statut |
|---------|--------|
| Config URL/key/bucket | GO |
| Bucket privé `elfis-vault` | GO |
| Upload / sign / download / delete diagnostic | GO |
| Logs sans secrets | GO |
| Flux métier email inchangé | GO |
| Envoi email réel bout-en-bout | Non exécuté ici (prérequis Vault OK) |

**Décision phase A1.1.5 : GO** (blocage Storage Vault levé).
