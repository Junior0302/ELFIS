# 02 — Architecture d’information Espaces

## Hub

**Espaces ELFIS** — un seul point d’accès aux métiers de l’entreprise.

## Domaines (cartes)

| Espace | Rôle | Signature |
|--------|------|-----------|
| Finance | Facturation, banque, TVA | Moteur ComptaPilot |
| Commercial | Pipeline, prospects | Moteur SalesPilot |
| Documents | Coffre plateforme | Moteur DocPilot |
| RH | Équipes, congés | Moteur HRPilot |
| Analyse | KPI / insights | — |
| Support | Tickets | Moteur SupportPilot |

## Règles

1. ELFIS n’est **pas** une carte app — Accueil via **Accueil ELFIS** (header + footer).
2. Une carte = un métier / domaine, pas un nom de produit en titre.
3. Badge **Bientôt** si aucune route d’entrée réelle.
4. Raccourcis = routes SPA existantes uniquement.
5. Continuer = **Reprendre dans {Espace}** (lastProduct → espace).

## Sections panel

1. Header (titre + Accueil ELFIS)
2. Recherche
3. Continuer
4. Espaces métier (ouvrables)
5. Bientôt disponibles
6. Footer plateforme
