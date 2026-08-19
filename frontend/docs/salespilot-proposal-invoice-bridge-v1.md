# SalesPilot → ComptaPilot — Proposal-to-Invoice Bridge V1 (S1.6.1)

## Responsabilités

| Domaine | Propriétaire |
|---------|--------------|
| Proposition commerciale, versions, PDF Vault, conversion UX | **SalesPilot** |
| Customer, Contact, facture brouillon, numérotation FAC-* | **ComptaPilot** |

Aucune facture automatique. Aucun client silencieux. Aucune fusion de doublons.

## Flux

1. Proposition `accepted` + version verrouillée  
2. `GET …/conversion-state`  
3. Résolution client (`use_linked_customer` | `use_existing_customer` | `create_new_customer`)  
4. `POST …/conversion-preview` (montants backend uniquement)  
5. Confirmation utilisateur (`ConfirmDialog`)  
6. `POST …/convert-to-invoice` → facture **draft**  
7. `linked_invoice_id` + statut `converted`  
8. Événements + timeline — **pas d’envoi**

## Résolution client

- Toujours un mode explicite côté payload.  
- `customer_id` hors organisation → 403.  
- Exact match : sélection possible.  
- Possible match : `confirm_possible_match=true` obligatoire.  
- Création : payload contrôlé (nom, email, téléphone, adresse, TVA) — pas de notes commerciales.

## Preview & mapping

| Source | Cible |
|--------|-------|
| `proposal_number` | `source_number` / notes |
| `version_id` | `source_version_id` |
| `line.name` | description ligne |
| qté / PU / remise / TVA | lignes ComptaPilot |
| totaux | revalidés ; écart > 0,02 € → refus |

Le frontend n’effectue **aucun** calcul.

## Idempotence

- `linked_invoice_id`  
- `source_type=sales_proposal` + `source_id`  
- `conversion_idempotency_key`  
- Index unique PostgreSQL partiel  

Requête répétée → même facture, `already_converted=true`.

## Transaction

Verrouiller proposition → résoudre client → valider preview → créer facture (`commit=False`) → lier → `converted` → commit → événements (safe_publish / outbox). Échec facture → rollback, proposition reste `accepted`.

## Permissions

- SalesPilot : `sales.proposals.read`, `sales.proposals.convert`  
- ComptaPilot : `invoice.create` (conversion + création client)

## Événements

- `sales.proposal.customer.linked.v1`  
- `sales.proposal.customer.created.v1`  
- `sales.proposal.conversion.started.v1`  
- `sales.proposal.converted.v1`  
- `sales.proposal.conversion.failed.v1`  
- `billing.invoice.created_from_proposal.v1`

## Limitations V1

- Un taux TVA dominant (1ʳᵉ ligne) pour le calcul ComptaPilot float.  
- Une facture principale par proposition.  
- Pas d’envoi, paiement, signature, fusion, S1.7.

## Récupération

Lien orphelin (`linked_invoice_id` sans document) → erreur contrôlée `orphan_invoice_link`, pas de recreation silencieuse.

## Roadmap

Émission contrôlée, multi-taux TVA natif, activity Compta unifiée, S1.7 hors scope.
