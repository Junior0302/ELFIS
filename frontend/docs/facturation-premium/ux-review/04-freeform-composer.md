# 04 — Freeform Composer

## Structure

Plus de sidebar wizard 10 étapes. Sections : Client, Lignes, Conditions, Notes, Paiement, Totaux, Aperçu, Contrôles.

## Progression

5 jalons header (données réelles) : Type, Client, Lignes, Champs, Contrôles.

## Ouverture

- `?type=facture|devis|avoir` requis
- Sinon redirect `/facturation/documents?create=1`
- Titres : Nouvelle facture / Nouveau devis / Nouvel avoir
- `showSidebar={false}` ; layout édition | preview sticky

## Backend

États workflow / `deriveWizardControls` / APIs inchangés.
