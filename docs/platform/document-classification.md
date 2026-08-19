# Document Classification (RC2.5.2)

## Principe

Classification **déterministe et heuristique** — pas d’OCR, pas d’IA externe.
Les scores sont des **scores heuristiques**, pas des probabilités statistiques.

## Pipeline

`document_classification_v1` :

1. validate_document_available
2. inspect_storage_metadata
3. classify_document
4. persist_classification
5. finalize_processing

`document_basic_v1` reste disponible.

## Classifiers

- MetadataDocumentClassifier
- FilenameRuleClassifier (jamais de filename complet en preuve)
- StructuralFileClassifier (MIME/conteneur uniquement)
- CompositeDocumentClassifier

## Facture fournisseur / client

Le mot « facture » / « invoice » seul → type générique `invoice` + alternatives `supplier_invoice` / `customer_invoice` + **revue obligatoire**.
Direction seulement avec signaux fiables (type déclaré, lien métier).

## Idempotence

Même `(document_version_id, classifier_key, classifier_version)` → retourne le résultat actif existant sauf `force=true` (reclassify).

## Type effectif

- `confirmed_type` prioritaire
- sync `DocumentRecord.document_type` à la confirmation humaine
- auto-confirm désactivé par défaut (`DOCUMENT_CLASSIFICATION_AUTO_CONFIRM=false`)
