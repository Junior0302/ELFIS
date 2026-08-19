# Sécurité — Document OCR (RC2.5.3)

## Sensibilité

Le texte OCR peut contenir PII, données bancaires, fiscales, salariales, pièces d’identité, contrats.
Le traiter comme contenu documentaire sensible.

## Interdits

Pas de texte OCR dans : logs, traces, métriques, messages d’erreur, audits, notifications, résumés de job ordinaires, listes API.

## IAM

| Permission | Usage |
|------------|--------|
| `document_processing.ocr.read` | Métadonnées résultats / pages |
| `document_processing.ocr.create` | Lancer un job OCR |
| `document_processing.ocr.retry` | Relancer |
| `document_processing.ocr.reject` | Rejeter |
| `document_processing.ocr.text.read` | Stream texte (élevée) |
| `document_processing.ocr.providers.read` | Catalogue providers |
| `document_processing.ocr.providers.manage` | Super admin |

Un `platform_admin` **sans** `ocr.text.read` ne lit pas le contenu client.

## Quarantaine

Document / objet quarantined → pipeline normal **bloque** (`blocked`), aucun open fichier provider, audit sans contenu.

## PDF malveillant (défenses minimales)

Taille / pages / timeout ; parser lecture seule ; pas de JS / réseau / ressources externes ; tempfile isolé ; erreurs sanitisées.
Ne remplace pas un antivirus.

## Audit (métadonnées bornées)

Actions `DOCUMENT_OCR_*` : ids, provider, method, page_count, text_length, score arrondi, error_code, duration_ms, requires_review.
Jamais : texte, mots, filename, bbox complets, chemin, object_key, URL, token, secret.

## Isolation

Aucun accès cross-tenant. Résultat d’une version jamais appliqué à une autre.
