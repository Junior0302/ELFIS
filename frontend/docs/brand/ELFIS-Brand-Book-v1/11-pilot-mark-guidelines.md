# 11 — Pilot Mark Guidelines

**Phase :** B0.2  
**Rôle :** guide officiel d’utilisation du Pilot Mark (dès que le tracé B0.3 existe).

Aucun fichier image dans cette phase. Ces règles s’appliquent au glyphe dès sa validation.

---

## 1 — Zone de protection

Soit **H** = hauteur du bounding box du Mark.

| Zone | Mesure |
|------|--------|
| Protection minimale | **0,5 H** de chaque côté |
| Protection recommandée (digital) | **0,75 H** |
| Protection print / signalétique | **1 H** |

Aucun texte, picto, filet ou photo ne pénètre cette zone.

Exception contrôlée : pastille de notification (système) en coin — ne doit pas couvrir plus de 20 % du Mark.

---

## 2 — Taille minimale

| Support | Minimum |
|---------|---------|
| Écran (Mark Principal) | **24 px** de hauteur |
| Écran (version Micro) | **16 px** |
| Favicon | 16×16 / 32×32 (Micro si besoin) |
| Print | **8 mm** de hauteur |
| Broderie / goodies | Valider lisibilité réelle ; sinon wordmark seul |

Sous le minimum → utiliser le **wordmark** ou le nom texte, pas un Mark déformé.

---

## 3 — Fonds

| Fond | Variante Mark |
|------|----------------|
| Clair (blanc, secondary) | Monochrome foncé (navy / primary / noir) |
| Sombre (primary, navy) | Monochrome clair (blanc / secondary) |
| Photo | Mark dans pastille neutre opaque ou monochrome à fort contraste |
| Teinté produit léger | Mark primary du produit **ou** navy — tester contraste |

Interdit : Mark low-contrast sur photo chargée sans pastille.

---

## 4 — Contraste

- Ratio texte/icône sur fond : viser **WCAG AA** minimum pour les UI.
- Watermark : opacité basse autorisée **uniquement** si non interactif et non critique à la compréhension.

---

## 5 — Interdictions (liste officielle)

### Déformations

- Étirement non uniforme  
- Skew / perspective libre  
- Rotation libre hors angles documentés (0° / usage animation ≤ 15°)

### Effets

- Ombres portées marketing non validées  
- Glow néon, bevel, extrude 3D  
- Contours multiples / stickers  
- Dégradés **dans** le glyphe maître (voir Symbol System — Option A)

### Composition

- Recadrage qui coupe le Mark  
- Duplication en motif sans validation Brand  
- Combinaison avec un autre logo sans zone de protection  
- Remplacement par emoji ou initiale comme « faux Mark »

### Couleur

- Arc-en-ciel non autorisé dans le glyphe  
- Vert ComptaPilot comme couleur du Mark sur SalesPilot (et inversement) hors contexte produit explicite  
- Couleurs hors Brand Book

---

## 6 — Usages autorisés (rappel)

| Usage | Variante typique |
|-------|------------------|
| Landing / Login ELFIS | Mark + wordmark ELFIS Core, navy |
| App Launcher | Icône Mark |
| Sidebar produit | Mark teinté produit + wordmark Pilot |
| Topbar plateforme | Mark navy / monochrome |
| Favicon | Micro |
| PDF / emails | Monochrome print |
| Loader | Animation « connexion » |
| Réseaux sociaux | Avatar / icône 1:1 |
| Goodies / vêtements / signalétique | Monochrome, grande taille, protection 1 H |

Détail des contextes : [10 — Symbol System §6 & §10 applications](./10-symbol-system.md) et section Applications ci-dessous.

---

## 7 — Applications futures (checklist Brand)

Avant tout déploiement :

### Digital produit

- [ ] Landing ELFIS  
- [ ] Login ELFIS  
- [ ] App Launcher  
- [ ] Sidebar Product Shell  
- [ ] Topbar Platform Shell  
- [ ] Workspace (favicon / empty states sobres)

### Documents & com’

- [ ] PDF  
- [ ] Emails transactionnels / marketing  
- [ ] Présentations

### Hors écran

- [ ] Icônes stores  
- [ ] Apps mobiles  
- [ ] Réseaux sociaux  
- [ ] Goodies  
- [ ] Vêtements  
- [ ] Signalétique

Pour chaque case : variante nommée + fond + taille min + protection.

---

## 8 — Gouvernance

| Demande | Décision |
|---------|----------|
| Nouveau usage non listé | Validation Brand avant production |
| Version Micro additionnelle | Une seule Micro officielle |
| Animation custom | Conforme motifs Symbol System §7 |
| Fork géométrique | **Refus** sauf révision Brand Book majeure |

---

## 9 — Lien B0.3

Dès le tracé livré, ce guide s’applique sans réécriture.  
B0.3 produit les fichiers ; B0.2 a figé les règles.
