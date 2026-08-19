# 08 — Nomenclature

## Formes officielles

Toujours écrire exactement :

| Correct | Incorrect |
|---------|-----------|
| **ELFIS Core** | Elfiscore, ELFISCORE, Elfis Core, elfis core |
| **ComptaPilot** | Compta Pilot, Comptapilot, COMPTA PILOT |
| **SalesPilot** | Sales Pilot, Salespilot |
| **DocPilot** | Doc Pilot, Docpilot |
| **HRPilot** | HR Pilot, HrPilot |
| **LegalPilot** | Legal Pilot |
| **MarketingPilot** | Marketing Pilot |
| **InventoryPilot** | Inventory Pilot |
| **ProjectPilot** | Project Pilot |
| **SupportPilot** | Support Pilot |
| **Pilot Mark** | Logo Compta, mark ComptaPilot (comme symbole mère) |

---

## Règles générales

1. **CamelCase** pour les noms de Pilot (`XxxPilot`).
2. **ELFIS Core** : deux mots, « Core » avec majuscule.
3. Pas d’espace dans les noms de Pilot.
4. En français, ne pas traduire les noms de produits.
5. Au pluriel : « les Pilot » (invariable recommandé dans la doc Brand) ou « les applications Pilot ».

---

## « by ELFIS Core »

### Forme

```text
by ELFIS Core
```

- `by` en minuscules
- `ELFIS Core` orthographe officielle

### Quand

Voir [03 — Architecture de marque](./03-architecture-de-marque.md).

### Interdit

- `by ELFIS`
- `by Elfis Core`
- `Powered by ComptaPilot`
- `une offre ComptaPilot by SalesPilot`

---

## Mentions UI courtes

| Contexte | Autorisé |
|----------|----------|
| Onglet navigateur | `SalesPilot` · `ComptaPilot` · `ELFIS Core` |
| Breadcrumb | Nom du Pilot ou de la page |
| Toast / erreur | Nom officiel du produit concerné |

---

## Identifiants techniques (hors Brand visible)

Les IDs code (`salespilot`, `elfis-core`, `comptapilot`) restent en kebab/lowercase.  
Ils **ne remplacent pas** les noms Brand dans l’UI utilisateur.

| UI (humain) | ID technique |
|-------------|--------------|
| ELFIS Core | `elfis-core` |
| ComptaPilot | `comptapilot` |
| SalesPilot | `salespilot` |

---

## Checklist rédactionnelle

Avant publication marketing ou UI copy :

- [ ] Orthographe exacte des noms
- [ ] Pas de réduction d’ELFIS à ComptaPilot
- [ ] `by ELFIS Core` correctement placé si Product Shell
- [ ] DocPilot / HRPilot / etc. conformes
