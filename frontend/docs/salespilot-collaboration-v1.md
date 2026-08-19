# SalesPilot Collaboration V1 (S1.9)

## Philosophie

CRM collaboratif **métier** : qui possède quoi, qui suit, qui revoit, qui commente. Aucun chat. Design System ELFIS 1.0 uniquement.

## Frontend livré

| Surface | Route / composant |
|---------|-------------------|
| Team Dashboard | `/sales/team` |
| Vues collab | `/sales/collab/views` |
| Commentaires | `SalesCommentsPanel` (Relationship / Deal / Proposal) |
| Assign / Review / Transfer / Follow | `SalesCollabActions` |
| Mentions | token `@[userId:Label]` + autocomplete |

## Mentions

Format strict backend : `@[12:Prénom Nom]`. Pas de markdown riche.

## Followers

Notifications seulement pour mention, assignation, revue, transfert — pas de spam.

## Interdictions respectées

S2 non commencé. Pas de chat, Slack, Teams, Google Workspace, emails auto, Sales AI V2.
