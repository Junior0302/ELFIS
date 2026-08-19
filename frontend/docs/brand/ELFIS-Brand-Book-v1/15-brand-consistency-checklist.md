# 15 — Brand Consistency Checklist

**Phase :** B0.3  
**Usage :** tout nouveau Pilot (ou révision de marque) **avant publication**.

Un Pilot n’est publiable que si **toutes** les cases obligatoires sont cochées.

---

## A — Identité & nomenclature

- [ ] Nom officiel conforme (`XxxPilot` ou `ELFIS Core`) — [08](./08-nomenclature.md)
- [ ] Aucune variante orthographique dans UI / marketing
- [ ] ID technique documenté (`kebab-case`) sans fuite dans l’UI Brand
- [ ] Fiche produit complète — [14](./14-product-brand-guidelines.md)

## B — Pilot Mark & logo

- [ ] Utilise le **Pilot Mark** unique — pas de symbole concurrent
- [ ] Respecte la grille 8×8 U / stroke / rayons — [10](./10-symbol-system.md)
- [ ] Mark monochrome maître (Option A) ; teinte = primary produit seulement
- [ ] Lockups nommés fournis ou prévus (`mark-only`, `mark-name-h`, `product-signed-h`, …) — [13](./13-logo-architecture.md)
- [ ] Signature `by ELFIS Core` selon règles Product Shell / marketing
- [ ] Zone de protection et tailles mini — [11](./11-pilot-mark-guidelines.md)
- [ ] Tests fond clair / fond sombre / 16 px

## C — Couleur & DNA

- [ ] Palette primary / secondary / accent figée au Brand Book — [05](./05-palette-officielle.md)
- [ ] Couleurs système (success, warning, danger) non redéfinies
- [ ] Design DNA respecté (angles, rayons, ombres, densités) — [06](./06-design-dna.md)
- [ ] Aucune contamination d’une primary d’un autre Pilot dans le shell

## D — Platform / Product

- [ ] Product Shell distinct ; Platform Shell non « avalé » par le Pilot — [07](./07-platform-vs-product.md)
- [ ] App Launcher = composant plateforme
- [ ] Surfaces publiques restent ELFIS Core si le Pilot n’est pas la page marketing dédiée

## E — Motion & composants

- [ ] Motifs motion système uniquement (apparition, connexion, transition couleur/wordmark)
- [ ] Pas de morphing du Mark vers un picto métier
- [ ] `prefers-reduced-motion` respecté
- [ ] Composants ELFIS Design System (pas de kit UI parallèle)

## F — Extensibilité

- [ ] Aucun fork géométrique « pour se différencier »
- [ ] Ajout futur possible sans toucher au Mark (règle B0.2)
- [ ] Documentation de la fiche + assets naming prête

## G — Gouvernance

- [ ] Validation Brand écrite
- [ ] Pas de merge runtime d’assets non validés
- [ ] Checklist archivée avec la version du Pilot

---

## Résultat

| Statut | Signification |
|--------|----------------|
| **GO** | Toutes les cases obligatoires cochées |
| **NO-GO** | Toute case logo / Mark / nomenclature / grille manquante |

Les cases Illustration / photo peuvent être « en cours » pour un MVP **uniquement** si Logo + Mark + Palette + Shell sont GO.

---

## Rappel anti-dérive

> Un Pilot qui « a besoin de son propre symbole » = **échec Brand**.  
> Différenciation = couleur + wordmark + contenu métier — jamais un second Mark.
