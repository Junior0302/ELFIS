# 12 — Final Direction

**P1.2.1** · Décision d’exploration Landing (pre-React).

---

## Deux meilleurs concepts

| Rang | Concept | Pourquoi |
|------|---------|----------|
| **1** | **02 — Connected Ecosystem** | Direction Brand officielle ; Mark central ; scalabilité N Pilot ; mémorisation max |
| **2** | **10 — Connected Business** | Récit métiers humain ; lisibilité business ; même promesse sans perdre la plateforme |

Écartés en dominant : 05 (trop IA), 06 (friction DNA), 09 (hero stats), 07 seul (coût/a11y).

---

## Fusion recommandée

**Nom de direction Landing :**  
`Connected Ecosystem × Business`  
*(code : `LAND-CEB`)*

### Principe

> **Le Mark connecte. Les métiers incarnent.**  
> Hero = orbite / ancrage symbole (C2).  
> Corps = parcours métiers & Pilot (C10).  
> Respiration = greffon Minimal (C01).  
> Une section flux (C08) **sous** le fold — pas à la place du Mark.

---

## Structure page fusionnée (HF cible)

```
1. NAV          Mark · Écosystème · Métiers · Sécurité · Login · CTA
2. HERO         Mark centre + pastilles Pilot (dosées) + phrase + 1 CTA
                → beaucoup d’air (Minimal)
3. PROMESSE     Une plateforme. Plusieurs expertises.
4. MÉTIERS      Frise / grille Pilot (Connected Business)
5. PARCOURS     Sales → Compta → Doc (journée connectée)
6. FLUX         Diagramme data flow sobre (emprunt C08)
7. SHELLS       Mock Platform + switch Product (Mark stable)
8. LAUNCHER     Preview grille apps
9. CONFIANCE    Sécurité / org (greffon Executive léger)
10. CTA FINAL   Entrer dans ELFIS
11. FOOTER      Pilot links · légal · Mark
```

---

## Hero fusion — wireframe

```
┌────────────────────────────────────────────────┐
│ [Mark] ELFIS Core          Login    [Entrer]   │
│                                                │
│            ○ Doc                               │
│     ○ Sales   [ PILOT MARK ]   ○ Compta        │
│            ○ …                                 │
│                                                │
│   Une plateforme. Plusieurs expertises.        │
│   [ Entrer dans ELFIS ]                        │
└────────────────────────────────────────────────┘
```

Règles : pas de cards/stats/pills décoratives ; halo soft ; teintes palette only.

---

## Motion fusion

- Hero : stagger pastilles (C2/C7 dosé) ≤ 400 ms total  
- Sections : fade une fois  
- Pas de boucle agressive ; reduced-motion = orbite statique  

---

## Emprunts limités (non-dominants)

| Depuis | Emprunt | Où |
|--------|---------|-----|
| 01 | Vide, CTA unique | Hero, login link |
| 03 | Bloc confiance / démo | Section 9 |
| 04 | Mentions workspace/org | Section 9 |
| 08 | Diagramme flux | Section 6 |
| 05/06/09 | — | Pas en dominant |

---

## Critères d’acceptation avant React

- [ ] Lecture « plateforme + famille Pilot » en < 5 s  
- [ ] Mark mémorisable ; pas « compta only »  
- [ ] Hero conforme Brand (budget éléments)  
- [ ] N Pilot ajoutables sans redesign  
- [ ] Maquettes HF P1.2.x validées stakeholder  

---

## Suite

1. Maquettes HF `LAND-CEB` (desktop + mobile) — phase visuelle suivante  
2. Puis seulement implémentation React Landing  

**Aucun développement dans P1.2.1.**

**Arrêt ici.**
