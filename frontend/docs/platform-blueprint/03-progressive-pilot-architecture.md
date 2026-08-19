# 03 — Architecture progressive des Pilots

**ELFIS Platform Blueprint V1**

---

## Principe

ELFIS se déploie **progressivement**. Une organisation n’active pas tous les Pilots le premier jour.

```
Jour 1          → Core + 1 Pilot (ex. Compta)
Croissance      → + Sales, + Banking, + Inventory…
Maturité        → intelligence croisée maximale
```

L’architecture doit rendre ce parcours **naturel**, pas une migration douloureuse.

---

## Niveaux d’activation

| Niveau | État | Expérience utilisateur |
|--------|------|------------------------|
| **0 — Core seul** | Organisation, membres, shell, Relations (selon maturité) | Plateforme prête ; métiers limités |
| **1 — Pilot primaire** | Un Pilot métier actif | Valeur métier immédiate (Loi 1) |
| **2 — Duo / trio** | 2–3 Pilots | Enrichissement croisé (Loi 2) |
| **3 — Écosystème** | Plusieurs Pilots + Aura | Intelligence transversale |

---

## Règles d’architecture progressive

1. **Activation = opt-in** — jamais d’obligation cachée d’installer un second Pilot.
2. **Dégradation gracieuse** — si Inventory n’est pas actif, Compta utilise son flux local minimal (articles / lignes) sans prétendre gérer un entrepôt.
3. **Pas de big-bang data** — on n’attend pas la fusion totale des tables pour livrer de la valeur (ex. Shared Relations en projection avant Party unifié — voir S1.2).
4. **Contrats avant couplage** — on expose des capacités / contrats avant d’écrire des dépendances UI croisées.
5. **Aura après le socle** — Aura s’appuie sur des signaux stables ; elle ne remplace pas l’activation métier.

---

## Parcours typique (illustratif)

```
1. Créer l’organisation (Core)
2. Activer ComptaPilot → facturer / encaisser
3. Activer SalesPilot → pipeline → intent facture vers Compta
4. Activer Banking → rapprochement enrichi
5. Activer Inventory → catalogue / stock partagés
6. Aura → priorités et assistance cross-Pilot
```

Ce parcours est **architecture**, pas un calendrier commercial figé.

---

## Lien avec Zero verrou

L’activation progressive n’a de sens que si la **désactivation** est sûre (voir [05-zero-lock.md](./05-zero-lock.md)) : données conservées chez l’owner, pas de perte silencieuse.

---

## Travaux déjà engagés

- Surfaces partagées S1.1 / Relations S1.2 — [`../domain-separation/`](../domain-separation/README.md)
- Expérience shell & launcher — [`../platform/`](../platform/README.md)
- Orchestrator & intents — [`../platform-contracts/`](../platform-contracts/README.md) · [`../orchestrator/`](../orchestrator/)

---

## Synthèse

> On **active** des Pilots au fil des besoins.  
> On **n’impose** jamais l’écosystème entier.  
> Chaque étape reste conforme aux Trois Lois.
