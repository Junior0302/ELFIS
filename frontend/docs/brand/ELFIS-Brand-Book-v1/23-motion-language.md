# 23 — Motion Language

**Phase :** B0.5  
**Direction :** Connected Ecosystem  
**Intention :** le mouvement évoque la **circulation des données entre les Pilot** — pas le spectacle.

Aucun code dans cette phase.

---

## 1 — Philosophie

| Motif | Signification |
|-------|----------------|
| **Apparition** | L’information arrive clairement |
| **Connexion** | Des éléments liés se révèlent en séquence courte |
| **Circulation** | Suggestion de flux Cross-Pilot (launcher, écosystème, transition marque) |
| **Stabilité du Mark** | Le glyphe ne morph pas ; seuls couleur / wordmark changent |

Interdit : morphing Mark → picto métier · flash / oscillation de thème · particules / confetti · bounce élastique.

---

## 2 — Durées & easing

| Classe | Durée | Usage |
|--------|-------|-------|
| Micro | **120–180 ms** | Hover, focus, icône |
| Meso | **180–240 ms** | Cards, panels, drawers, launcher open |
| Macro | **240–360 ms** | Page, splash, première apparition dashboard |
| Stagger | **30–50 ms** / item | Launcher pastilles ; total < 400 ms |

**Easing :** ease-out / soft cubic — pas de spring cartoon.  
**Translate :** 4–12 px. **Scale :** ≤ 1.02 si besoin. Préférer opacité.  
**`prefers-reduced-motion` :** états finaux immédiats ; couper staggers.

---

## 3 — Catalogue

### Hover

- Fond secondary diluée, underline, opacité icône  
- Cards : élévation +1 discrète ou bordure — pas de glow  

### Cards

- Entrée : fade + 8 px Y une fois  
- Hover meso court  
- Pas d’animation permanente  

### Launcher

- Panel 180–240 ms  
- Pastilles en stagger « connexion »  
- Évoque la **famille** et la circulation entre apps  
- Fermeture plus rapide que l’ouverture  

### Transitions navigation

- Shell stable (topbar/sidebar) quand possible  
- Contenu : cross-fade court  
- Changement Pilot : **une** transition d’identité (primary + wordmark), Mark fixe  

### Loader

- Spinner / barre système  
- Mark Micro statique ou pulse opacity très lent  
- Interdit : Mark démonté en boucle  

### Apparition dashboards

- Une vague d’entrée (header → KPIs → charts) ≤ 360 ms total  
- Pas de re-anim à chaque filtre  

### Navigation / drawers

- Slide + fade meso  
- Focus trap visuel sans animation agressive  

### Marketing / vidéo

- Intro : motif connexion (éléments qui se lient)  
- Boucles social < 3 s ; Mark stable  
- Données qui « circulent » = filets / points abstraits, pas tubes néon  

---

## 4 — Circulation des données (métaphore visuelle)

Autorisé comme **suggestion** :

- Filets qui relient pastilles Pilot  
- Points qui se déplacent le long d’un chemin court  
- Highlight successif de modules liés  

Interdit :

- Tuyauterie 3D, réseau neuron, matrix rain  

---

## 5 — Do / Don’t

| Do | Don’t |
|----|-------|
| Fluidité courte utile | Parallax lourd |
| Mark fixe cross-Pilot | Morph Mark |
| Reduced motion | Ignorer a11y |
| Une intention / écran | Empiler 5 motions |

---

## 6 — Storyboard textuel type (B0.6)

```
t0  Mark seul (navy)
t1  Pastilles Pilot apparaissent (stagger)
t2  Filet de connexion soft
t3  Wordmark ELFIS Core
t4  CTA
```

Pas de fichier motion produit en B0.5.
