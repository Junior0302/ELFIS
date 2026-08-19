# Test plan — Document Studio V1 (F1.3.5)

## Automatisés (smoke UI)

| ID | Cas | Attendu |
|----|-----|---------|
| DS01 | Hero client présent | `[data-ds-studio-hero="client"]` + titre « Qui souhaitez-vous facturer » |
| DS02 | Marker studio | `[data-ds-studio="1"]` + `.elf-cmp-focus--studio` |
| DS03 | Stepper current | `[data-step-id="client"][data-step-status="current"]` |
| DS04 | PDF skeleton | `[data-ds-pdf-skeleton="1"]` visible dès ouverture |
| DS05 | PDF blocs structure | blocs client / lines / totals / footer |
| DS06 | Après client | smart card client + stepper completed sur client |
| DS07 | Conseil placeholder | `data-ds-conseil="placeholder"` + disclaimer |
| DS08 | Products hero | titre « Quels produits et services » |

## À tester manuellement

- [ ] Sensation studio (air, cartes, fond gris chaud) vs ancien formulaire
- [ ] Stepper ○ → ◐ → ✓ en naviguant Continuer / Retour
- [ ] Animation douce ~200ms ; reduced-motion OS → pas d’anim
- [ ] PDF : structure visible avant toute saisie ; client/lignes apparaissent progressivement
- [ ] Smart card client : pas de ★ / CA inventés si absents
- [ ] Smart card produits : disparaît si aucune ligne libellée
- [ ] Conseil clairement marqué comme exemple (pas de faux insights)
- [ ] Mode page freeform (`/facturation/nouveau`) hors studio inchangé
- [ ] Responsive étroit : colonnes empilées, hero lisible
- [ ] Focus a11y : heading étape focusable après navigation

## Régression

Relancer GC01–GC40 + machines step/modal existantes.
