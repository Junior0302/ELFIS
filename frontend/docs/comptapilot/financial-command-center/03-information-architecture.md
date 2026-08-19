# 03 — Architecture d’information

## Hiérarchie desktop (S1.2.5.1)

1. Header (titre, résumé, MAJ, Actualiser tout, lien `/finance`)
2. Bandeau org incomplete (conditionnel)
3. **Analyser** — 3 charts Engine (`revenue_vs_expenses`, `treasury`, `ca_evolution`)
4. **Essentiel** — grille KPI compacte + documents à traiter (**pas** sync)
5. **Décider aujourd’hui** — priorités | alertes | actions rapides
6. **Comprendre et prévoir** — Health Score (colonne) | Prévisions empty | Encaissements/décaissements empty
7. **Bas** — Traiter (~30%, inclut sync) | Activité récente (~42%) | Assistant (~28%)

## Hiérarchie mobile

Ordre CSS (`order`) : header → bandeau → **Décider** (priorités, alertes) → KPI critiques (trésorerie, impayés, TVA) → actions → autres → Comprendre → **Analyser** (graphiques) → Bas.

## Actions rapides autorisées (V1)

Facturation, dépôt justificatif, impayés, propositions d’écritures, banque, TVA ; CTA Assistant financier.

Interdit : actions Sales, Launcher, onboarding marketing.

## Navigation externe

| Cible | Rôle |
|---|---|
| `/finance` | Analyse détaillée |
| `/platform/organization` | Compléter org |
| `/copilote` | Expliquer / Assistant |
| Modules compta listés | Traiter / décider |
