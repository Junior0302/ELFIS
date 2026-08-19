# 10 — Règles de développement

**ELFIS Platform Blueprint V1** · Checklist obligatoire

---

## Avant chaque développement

Répondre **explicitement** à chaque point. Si un point échoue → redesign avant code.

### 1. Propriétaire

- [ ] Quel est l’**owner** de chaque donnée lue / écrite ?
- [ ] Ai-je vérifié la matrice ownership (Blueprint ch. 08 + domain-separation / platform-contracts) ?
- [ ] Est-ce que j’écris uniquement dans mon domaine ?

### 2. Autonomie (Loi 1)

- [ ] Le Pilot fonctionne-t-il **sans** les autres Pilots concernés ?
- [ ] Ai-je prévu une **dégradation gracieuse** si la capacité manque ?

### 3. Réutilisation / Zero ressaisie

- [ ] Est-ce que je **réutilise** une entité / capacité existante ?
- [ ] Est-ce que j’évite toute **nouvelle saisie** d’info déjà connue ?
- [ ] Est-ce que je **copie** une donnée owned ailleurs ? (si oui → stop)

### 4. Widgets / UI plateforme

- [ ] Si dashboard / métrique : est-ce que j’utilise le **Widget Framework** (ou extension documentée) ?
- [ ] Est-ce que je reste dans le **Design System** et le chrome plateforme ?
- [ ] Est-ce que la source / owner est visible ou traçable ?

### 5. Aura

- [ ] Est-ce que je confonds Aura avec un Pilot ? (interdit)
- [ ] Si j’ajoute un signal Aura : est-ce une **lecture / suggestion**, pas une écriture métier sauvage ?

### 6. Trois Lois (récap)

- [ ] **Loi 1** Autonomie respectée ?
- [ ] **Loi 2** Enrichissement (pas absorption) ?
- [ ] **Loi 3** Un seul propriétaire ?

### 7. Zero verrou

- [ ] Activer / désactiver ce Pilot (ou cette dépendance) ferait-il **perdre** des données ? (si oui → stop)

---

## Règles transverses

| Règle | Détail |
|-------|--------|
| Pas de Pilot→Pilot direct | Passer par Orchestrator / contrats |
| Pas de nouveau Pilot « en passant » | Décision produit + ownership + docs |
| Docs d’architecture avant couplage | Capacités et contrats avant UI croisée |
| Phase documentaire ≠ code | Ne pas « juste ajouter une table » pour un POC |

---

## Quand le Blueprint prime

En cas de conflit entre « vitesse de feature » et Blueprint :

1. Blueprint / Trois Lois
2. Contrats domain-separation & platform-contracts
3. Implémentation locale

---

## Synthèse

> Pas de merge sans checklist.  
> Pas de checklist cochée à vide.  
> Le Blueprint est la référence ; le code s’y plie.
