# Première impression ComptaPilot — Concept 6

Version unique : **« Prêt. Compris. Un clic. »**

## Test des 10 secondes

Un artisan doit répondre immédiatement :

1. **Apport** — hero + 4 bénéfices dirigeants  
2. **Confiance** — témoignage + zone « Pourquoi faire confiance… »  
3. **Action** — CTA `🚀 Commencer gratuitement pendant 14 jours` → `/abonnement`

## Structure — Landing page intégrée

Narration verticale (promesse, **pas** un espace de travail) :

| Zone | Contenu | Scroll |
|------|---------|--------|
| **1** | Hero + badges + CTA + Preview | 100 % viewport |
| **2** | Bénéfices (grands, respirants) | après scroll |
| **3** | Configuration / checklist | après scroll |
| **4** | Confiance puis témoignage | après scroll |

Le vrai dashboard commence **après** activation de l’essai.


## Navigation verrouillée

- Menus hors Accueil : locked + shake léger + tooltip `Disponible après activation de votre essai.`
- Allowlist : `/dashboard`, `/abonnement`, `/compte`, `/modules`
- Aucun appel Financial Engine sans entitlement

## Technique

- `TrialActivationState.tsx` + classes `fi-*`
- Constantes : `trialOnboarding.ts`
- Events : `trial_onboarding_viewed`, `trial_cta_clicked`, `locked_nav_item_clicked`, `feature_discovery_opened`
- Tests : `trialOnboarding.test.ts`
