# 02 — Les Trois Lois

**ELFIS Platform Blueprint V1** · Lois non négociables

Toute évolution produit, technique ou UX doit respecter ces trois lois.  
Elles priment sur les habitudes de « module monolithique » ou de duplication pragmatique.

---

## Loi 1 — Autonomie

> **Chaque Pilot doit pouvoir fonctionner seul.**

Un client qui n’active que ComptaPilot doit pouvoir facturer, encaisser et tenir sa compta **sans** Sales, Inventory ou Banking.

### Implications

- Pas de dépendance **dure** à un autre Pilot pour le chemin critique du Pilot.
- Les intégrations sont **optionnelles** (enrichissement), jamais bloquantes.
- Les écrans et APIs d’un Pilot ne doivent pas exiger qu’un autre Pilot soit installé.

### Exemple

| Situation | Conforme | Non conforme |
|-----------|----------|--------------|
| ComptaPilot seul | Facture un client saisi dans le flux Compta / Relations disponibles | Impossible de créer une facture sans SalesPilot |
| SalesPilot seul | Gère pipeline et devis | Bloqué tant qu’Inventory n’est pas activé |

---

## Loi 2 — Enrichissement

> **Quand un autre Pilot est actif, le Pilot courant s’enrichit — sans le remplacer.**

L’activation d’Inventory enrichit Compta (catalogue, stock, prix) ; elle ne transforme pas Compta en gestionnaire de stock.

### Implications

- Consommer une **capacité** exposée, pas absorber le domaine.
- Afficher des infos / actions provenant d’un autre Pilot **avec attribution claire** (source = owner).
- Ne pas cacher le Pilot propriétaire derrière une UI « monolithe ».

### Exemple

| Situation | Conforme | Non conforme |
|-----------|----------|--------------|
| Inventory actif | Compta propose les articles du catalogue Inventory ; le stock reste géré dans Inventory | Compta crée sa propre table stock « pour aller plus vite » |
| Banking actif | Compta affiche le rapprochement via Banking | Compta réimplémente toute la banque en local |

---

## Loi 3 — Un seul propriétaire

> **Chaque donnée a un unique propriétaire (owner).**

Pas de double vérité. Les autres Pilots **lisent** ou **demandent** ; ils ne deviennent pas co-owners silencieux.

### Implications

- Matrice d’ownership explicite (voir [08-data-ownership.md](./08-data-ownership.md)).
- Écritures métier réservées à l’owner (sauf mécanismes plateforme documentés).
- L’Orchestrator **coordonne** ; il **ne possède pas** les entités métier.

### Exemple

| Donnée | Owner | Lecteurs typiques |
|--------|-------|-------------------|
| Organisation | Core | Tous |
| Relation / Party (identité) | Core (Relations) | Sales, Compta |
| Facture fiscale | ComptaPilot | — |
| Opportunité | SalesPilot | — |
| Stock / SKU | Inventory (cible) | Compta, Sales |
| Paiement | Banking / Compta selon contrat ownership (voir ch. 08) | — |

Alignement avec les matrices déjà documentées :

- [`../domain-separation/01-domain-ownership-matrix.md`](../domain-separation/01-domain-ownership-matrix.md)
- [`../platform-contracts/05-ownership-model.md`](../platform-contracts/05-ownership-model.md)

---

## Les Trois Lois ensemble

```
Loi 1  Autonomie        → le Pilot vit seul
Loi 2  Enrichissement  → les autres Pilots le rendent meilleur
Loi 3  Un owner         → une vérité, zéro copie fantôme
```

Si une feature viole une loi, **elle ne part pas en production** — même « temporairement ».

---

## Checklist express

- [ ] Le Pilot fonctionne-t-il sans les autres ?
- [ ] L’intégration enrichit-elle sans absorber le domaine ?
- [ ] L’owner de chaque écriture est-il unique et documenté ?
