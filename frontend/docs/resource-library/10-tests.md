# 10 — Plan de tests RL01–RL40

Tous les items : **À tester manuellement** (sauf automatisés listés en bas).

| ID | Scénario | Statut |
|----|----------|--------|
| RL01 | Smart Library charge `/catalogue` | À tester manuellement |
| RL02 | Redirect `/facturation/catalogue` → `/catalogue` | À tester manuellement |
| RL03 | Redirect `/catalog` et `/sales/catalog` | À tester manuellement |
| RL04 | Nav « Catalogue » ouvre Smart Library | À tester manuellement |
| RL05 | Liste produits/services depuis API réelle | À tester manuellement |
| RL06 | Vue cartes lisible | À tester manuellement |
| RL07 | Vue liste compacte | À tester manuellement |
| RL08 | Recherche filtre par nom | À tester manuellement |
| RL09 | Filtre type produit/service | À tester manuellement |
| RL10 | Filtre TVA | À tester manuellement |
| RL11 | Filtre prix min/max | À tester manuellement |
| RL12 | Tri nom / prix / updated | À tester manuellement |
| RL13 | Section Packs désactivée / empty honnête | À tester manuellement |
| RL14 | Section Favoris désactivée | À tester manuellement |
| RL15 | Section Récents désactivée | À tester manuellement |
| RL16 | Section Plus utilisés désactivée | À tester manuellement |
| RL17 | Empty state + Créer | À tester manuellement |
| RL18 | Empty state + Importer (placeholder) | À tester manuellement |
| RL19 | Import CSV bouton disabled | À tester manuellement |
| RL20 | Import InventoryPilot bouton disabled | À tester manuellement |
| RL21 | Création produit via formulaire | À tester manuellement |
| RL22 | Modification produit | À tester manuellement |
| RL23 | Duplication produit | À tester manuellement |
| RL24 | Voir détail | À tester manuellement |
| RL25 | Historique disabled | À tester manuellement |
| RL26 | Permission sans `invoice.create` : pas d’écriture | À tester manuellement |
| RL27 | ProductPicker dans Composer ajoute une ligne | À tester manuellement |
| RL28 | Création inline Composer → ligne + refresh | À tester manuellement |
| RL29 | Lien Ouvrir catalogue depuis picker | À tester manuellement |
| RL30 | Inventory preferred → fallback local honnête | À tester manuellement |
| RL31 | Responsive mobile nav sections | À tester manuellement |
| RL32 | Pagination suivant/précédent | À tester manuellement |
| RL33 | Aucune donnée inventée favoris | À tester manuellement |
| RL34 | SalesDocLinesEditor legacy non cassé | À tester manuellement |
| RL35 | CustomerPicker Composer non régressé | À tester manuellement |
| RL36 | Labels source opaques (pas de fuite technique) | À tester manuellement |
| RL37 | `tsc` / build OK | Automatisé |
| RL38 | Tests unit Resource System verts | Automatisé |
| RL39 | Tests ProductSource / ProductPicker verts | Automatisé |
| RL40 | Pas de régression platform-search | Automatisé |

## Automatisés

- `frontend/src/resource-library/resource-library.unit.test.ts`
- `frontend/src/resource-library/resource-library.integration.test.tsx`
- `frontend/src/platform-search/platform-search.*.test.*`
