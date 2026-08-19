# HOME.0 — Data honesty

## Règle absolue

**Ne jamais inventer** de KPI métier (ex. « 2 factures », « 3 prospects »).

Si une donnée n’est pas branchée → empty state honnête ou omission.

## Matrice

| Zone | Comportement |
|------|----------------|
| Signaux hero | Uniquement auth / org / sync / unread / absence de session |
| Temps estimé | **Omise** (non calculable sans modèle réel) |
| Résumé journée | Statuts dérivés de `lastProduct` + org ; Documents = « Non agrégé » |
| Continuer | Empty si pas de `lastProduct` |
| Espaces | Disponibilité catalog ; RH bientôt ; pas de faux compteurs |
| Timeline | Notifications API + session + sync ; empty si rien ; **pas de HOME_TIMELINE_MOCK** |
| Intelligence | Tips = signaux ; disclaimer « pas d’IA générative » ; « Tout traiter » seulement si unread > 0 |
| Health | Connexion / Org / Sync (/ Notifications si flux connu) — **pas** stockage/IA/emails/paiements inventés |
| Notifications panel | Plus de fallback mock trompeur |

## Empty states

Chaque empty explique *pourquoi* c’est vide et *quoi faire ensuite* (ouvrir un espace, attendre un pulse, etc.).
