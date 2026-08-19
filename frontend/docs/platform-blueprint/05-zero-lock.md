# 05 — Zero verrou

**ELFIS Platform Blueprint V1**

---

## Définition

> **Zero verrou** : activer ou désactiver un Pilot ne doit entraîner **aucune perte de données** du propriétaire légitime, ni prendre l’organisation en otage.

L’utilisateur doit pouvoir faire évoluer son stack ELFIS (ajouter Sales, retirer un Pilot non critique, etc.) sans destruction silencieuse.

---

## Ce que Zero verrou garantit

| Action | Garantie |
|--------|----------|
| Activer un Pilot | Les données Core / autres Pilots restent intactes ; le nouveau Pilot s’abonne aux capacités |
| Désactiver un Pilot | Les données **owned** par ce Pilot sont **conservées** (archivage / gel d’accès), pas effacées par défaut |
| Réactiver | Reprise sur l’état conservé, sans ressaisie massive |
| Pilot absent | Les autres Pilots continuent (Loi 1) avec dégradation gracieuse |

---

## Ce que Zero verrou n’est pas

- Ce n’est **pas** « tout reste éditable comme si le Pilot était actif ».
- Ce n’est **pas** l’obligation de garder des UI métier d’un Pilot désactivé.
- Ce n’est **pas** un export magique multi-format à chaque clic (peut être un chantier ultérieur).

C’est : **pas de perte**, **pas de verrou commercial/technique** sur les données de l’entreprise.

---

## Règles de conception

1. **Données chez l’owner** — stockées dans le domaine du Pilot / Core, pas « dispersées » dans le consommateur.
2. **Désactivation = retrait d’accès / features**, pas `DROP TABLE`.
3. **Consommateurs** — si Inventory est désactivé, Compta cesse d’appeler ses capacités ; elle ne doit pas corrompre ni supprimer le catalogue Inventory.
4. **Migrations** — tout déplacement de surface UI (ex. vers Core) **sans copie** de donnée (règle déjà posée en domain-separation).
5. **Communication UX** — prévenir clairement ce qui devient en lecture seule / inaccessible après désactivation.

---

## Exemples

| Scénario | Comportement attendu |
|----------|----------------------|
| Désactiver SalesPilot | Opportunités / devis Sales conservés ; Compta continue de facturer |
| Désactiver Inventory | Catalogue Inventory gelé ; Compta repasse sur son flux local minimal |
| Réactiver Banking | Connexions / historique Banking toujours là |

---

## Lien avec les autres chapitres

- Autonomie — [02-three-laws.md](./02-three-laws.md) (Loi 1)
- Activation progressive — [03-progressive-pilot-architecture.md](./03-progressive-pilot-architecture.md)
- Ownership — [08-data-ownership.md](./08-data-ownership.md)

---

## Synthèse

> **Activer / désactiver ≠ détruire.**  
> Les données restent chez leur propriétaire.  
> La plateforme ne prend jamais l’entreprise en otage.
