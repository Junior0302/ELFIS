# Plan de tests manuels DP01–DP40 — Dashboard Premium S1.2.6

**Statut de chaque item :** À tester manuellement  
**Environnement :** `/dashboard` ComptaPilot, org avec entitlement financier.

| ID | Zone | Scénario | Statut |
|---|---|---|---|
| DP01 | Desktop | Header : titre Financial Command Center visible, respirant | À tester manuellement |
| DP02 | Desktop | Sync / MAJ affichée depuis overview (pas inventée) | À tester manuellement |
| DP03 | Desktop | Organisation active réelle (auth / membership) | À tester manuellement |
| DP04 | Desktop | Badge Engine Ready si overview OK | À tester manuellement |
| DP05 | Desktop | Badge honnête si erreur / chargement | À tester manuellement |
| DP06 | Desktop | Source « Financial Engine » visible | À tester manuellement |
| DP07 | Desktop | Lien Analyse détaillée → `/finance` | À tester manuellement |
| DP08 | Desktop | Bouton Actualiser recharge overview | À tester manuellement |
| DP09 | Desktop | Exporter → toast « bientôt » (pas de faux fichier) | À tester manuellement |
| DP10 | Analyser | Revenus vs Dépenses full-width héros | À tester manuellement |
| DP11 | Analyser | Trésorerie + Évolution CA en 2 colonnes | À tester manuellement |
| DP12 | Analyser | Hauteur charts confortable (pas mini) | À tester manuellement |
| DP13 | Analyser | Empty / historique insuffisant honnête | À tester manuellement |
| DP14 | Essentiel | KPI même taille / hauteur / padding | À tester manuellement |
| DP15 | Essentiel | Valeurs = overview uniquement | À tester manuellement |
| DP16 | Essentiel | Banques présentes seulement si sync réel | À tester manuellement |
| DP17 | Essentiel | Sync toujours visible dans Traiter | À tester manuellement |
| DP18 | Décider | Priorités densifiées, hover discret | À tester manuellement |
| DP19 | Décider | Alertes densifiées | À tester manuellement |
| DP20 | Décider | Actions rapides cliquables | À tester manuellement |
| DP21 | Health | Grande jauge + score + grade | À tester manuellement |
| DP22 | Health | Facteurs + disclaimer comptable | À tester manuellement |
| DP23 | Health | Conseils = recommendations API | À tester manuellement |
| DP24 | Health | Pas d’évolution inventée | À tester manuellement |
| DP25 | Prévisions | Empty premium + illustration | À tester manuellement |
| DP26 | Prévisions | CTA Connecter une banque → `/banque` | À tester manuellement |
| DP27 | Prévisions | Aucun montant 30/60/90 fictif | À tester manuellement |
| DP28 | Activité | Timeline icône / type / heure / badge | À tester manuellement |
| DP29 | Activité | Données = `recent_activity` uniquement | À tester manuellement |
| DP30 | Design | Ombres / radius / espacements cohérents | À tester manuellement |
| DP31 | Design | Pas purple / glow excessif | À tester manuellement |
| DP32 | Motion | Hover / fade discrets | À tester manuellement |
| DP33 | Motion | `prefers-reduced-motion` = pas d’anim | À tester manuellement |
| DP34 | Laptop | Layout 1280–1440 lisible | À tester manuellement |
| DP35 | Tablet | KPI / charts se réorganisent | À tester manuellement |
| DP36 | Mobile | Priorités avant graphiques | À tester manuellement |
| DP37 | Dark | Si thème dark produit existe : contraste OK | À tester manuellement |
| DP38 | Perf | Refresh widget indépendant sans freeze | À tester manuellement |
| DP39 | Build | `npm run build` vert | À tester manuellement |
| DP40 | Régression | `/finance` inchangé fonctionnellement | À tester manuellement |

## Automatisés associés

- `FinancialCommandCenter.test.tsx` (layout s126, header, analyser, timeline, banques)
- `widget-framework.test.tsx`
- `priorities.test.ts`
