# 06 — Design DNA

L’ADN partagé garantit que tous les Pilot « se ressemblent en famille » sans se confondre.

B0.1 fixe les **règles**. Les tokens techniques seront dérivés plus tard.

---

## Formes

- Langage géométrique **sobre** : rectangles, coins adoucis, rares cercles pour avatars / états.
- Pas de formes « stickers » marketing agressives sur les shells métier.
- Le Pilot Mark impose la géométrie du symbole ; l’UI ne le contredit pas.

---

## Angles & rayons

| Surface | Intention |
|---------|-----------|
| Cartes / panneaux | Rayon moyen, cohérent produit |
| Boutons | Rayon moyen, jamais « pill » systématique |
| Inputs | Alignés sur les boutons |
| Badges | Rayon plus faible que les cartes |
| Modales / drawers | Même famille que les cartes |

Principe : **une famille de rayons**, pas une collection arbitraire.

---

## Ombres

- Ombres **légères**, fonctionnelles (élévation), jamais néon / glow produit.
- Prefers-reduced-motion : pas d’ombre animée ostentatoire.
- Les Pilot n’introduisent pas leur propre système d’ombre.

---

## Espacements

- Grille d’espacement **8-point** (ou multiple cohérent déjà en Design System).
- Densité plus élevée autorisée dans les workspaces métier ; plus d’air sur les surfaces publiques.
- Les sidebars partagent une logique d’espacement commune (Platform / Product).

---

## Animations

| Autorisé | Interdit |
|----------|----------|
| Transitions courtes d’état (hover, focus, open) | Flash de couleur / thème |
| Entrées de page mesurées | Morphing du Pilot Mark |
| Reduced motion respecté | setInterval de re-thème |
| | Oscillation primary |

Le changement de produit (Compta → Sales) est un **changement d’identité unique**, pas une animation de couleur continue.

---

## Icônes

- Style linéaire cohérent (même stroke, mêmes coins).
- Pas d’emoji comme navigation primaire.
- Couleur d’icône = texte / accent, pas primary pleine sauf état actif contrôlé.

---

## Illustrations

- Style **platform_minimal** pour ELFIS Core.
- Styles métier autorisés par Pilot (finance, sales, …) mais dans une même grammaire (traits, densités, pas de collage clipart).
- Les illustrations n’écrasent pas le wordmark ni le Pilot Mark.

---

## Graphiques

- Palettes chart dérivées de la primary / accent produit.
- Axes et labels en neutres.
- Jamais de vert Compta dans un graphique Sales « par défaut ».

---

## Photographies

- Réalistes, professionnelles, lumière naturelle préférée.
- Éviter les banques d’images génériques « handshake stock » saturées.
- Sur landing ELFIS : photos d’écosystème / travail, pas uniquement compta.

---

## Typographie (intention)

- Display expressif pour les surfaces publiques ELFIS.
- UI lisible pour les shells métier.
- Une hiérarchie claire : plateforme ≠ produit ≠ contenu métier.

*(Les familles exactes restent celles du Design System tant que B0.4 ne les révise pas.)*

---

## Synthèse DNA

> **Même famille. Identités distinctes. Zéro confusion plateforme / produit.**
