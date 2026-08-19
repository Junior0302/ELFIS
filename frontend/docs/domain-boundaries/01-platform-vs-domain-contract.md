# 01 — Contrat plateforme / domaine

## Décision

| Surface | Propriétaire | Visible dans |
|---------|--------------|--------------|
| Organisation, membres, rôles | ELFIS | Menu ELFIS uniquement |
| Relations (annuaire partagé) | ELFIS | Menu ELFIS ; vues métier en lecture |
| Documents Vault générique | ELFIS | `/platform/documents` |
| Communications | ELFIS | Menu ELFIS |
| Paramètres compte / org / sécurité | ELFIS | `/platform/settings` |
| Facturation, banque, TVA, compta | Finance | Nav Finance |
| Pipeline, prospects, propositions | Commercial | Nav Commercial |

## Règles

1. Une surface transversale n’apparaît **pas** comme entrée permanente dans un domaine.
2. Accès occasionnel → lien contextuel, drawer, ou route ELFIS explicite.
3. Pas de second CRM / Vault / Organisation.
4. Pas de suppression d’API, table ou calcul.
5. Client → Devis → Facture reste intact.
6. Headers domaine : **Finance** / **Commercial** ; signature discrète **Moteur ComptaPilot** / **Moteur SalesPilot**.
