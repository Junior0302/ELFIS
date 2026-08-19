# 06 — Page Membres et équipes

Route : `/platform/members` → `PlatformMembersPage` → `AdminEquipePage`.

## PageHeader

- Eyebrow : **ENTREPRISE**
- Titre : **Membres et équipes**
- Description : Invitez des collaborateurs et gérez leurs accès à ELFIS.

## Invitation

- Surface blanche, bordure `--elfis-border`
- Primaire navy / bleu ELFIS (`ElfisButton`)
- Champs `ElfisField`
- Aucun fond vert Finance

## Table

Colonnes : Membre · Rôle ELFIS · (Accès espaces si flag) · Statut · Date d’adhésion · Actions  
Données réelles uniquement.

## Cartes rôles

Cinq cartes hauteur égale, surface neutre, Propriétaire marqué « Rôle protégé ».

CSS : `frontend/src/pages/elfis-members.css`
