# 04 — Zero ressaisie

**ELFIS Platform Blueprint V1**

---

## Définition

> **Zero ressaisie** : une information déjà connue de la plateforme ne doit jamais être retapée par l’utilisateur dans un autre Pilot, sauf correction volontaire chez l’owner.

La ressaisie est un symptôme de **mauvaise ownership** ou d’**absence de contrat de lecture**.

---

## Pourquoi c’est non négociable

| Problème de la ressaisie | Conséquence |
|--------------------------|-------------|
| Double saisie | Erreurs, dérive des fiches |
| Double vérité | Reporting faux, support impossible |
| Friction UX | Sensation d’outils séparés, pas de plateforme |
| Dette technique | Sync manuelle, scripts de « reconciliation » |

---

## Règles opérationnelles

1. **Lire chez l’owner** — ne pas recopier la fiche « pour simplifier ».
2. **Projection, pas clone** — les vues métier (ex. Clients Compta) peuvent enrichir des attributs **de leur domaine**, pas dupliquer l’identité.
3. **Identifiant stable** — référencer l’entité (id / party / source), pas recopier le nom partout comme source de vérité.
4. **Formulaires intelligents** — préremplir depuis Relations / Core / Capacités ; n’éditer que les champs du Pilot courant.
5. **Interdit** : « créer un second client Sales » alors qu’un client Compta existe déjà, sans stratégie Relations documentée.

---

## Exemples

### Conforme

```
Client créé / projeté via Relations (Core)
    → Sales attache une opportunité (réf. relation)
    → Compta émet une facture (réf. relation + attrs billing)
    → L’utilisateur ne retape ni SIRET ni adresse
```

### Non conforme

```
Sales crée « Acme SARL »
Compta crée « ACME Sarl » (autre fiche)
Banking crée « Acme » (troisième)
→ trois vérités, trois ressaisies
```

---

## Alignement repo

Travaux déjà engagés sur la réduction de la ressaisie / double vérité :

- Shared Relations (projection lecture, pas fusion tables prématurée) — [`../domain-separation/14-relations-shared-view.md`](../domain-separation/14-relations-shared-view.md)
- Contrat Shared Relations — [`../domain-separation/19-shared-relations-contract.md`](../domain-separation/19-shared-relations-contract.md)
- Ownership — [`../domain-separation/01-domain-ownership-matrix.md`](../domain-separation/01-domain-ownership-matrix.md)

**S1.3** (Party unifié / fusion tables) est une **suite future** — hors phase P0 et hors ce document d’implémentation.

---

## Test mental avant un écran

> « Est-ce que l’utilisateur va retaper quelque chose qui existe déjà ailleurs dans ELFIS ? »  
> Si oui → redesign (lecture / capacité / deep-link), pas un nouveau formulaire isolé.
