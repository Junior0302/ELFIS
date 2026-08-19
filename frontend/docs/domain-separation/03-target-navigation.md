# 03 — Navigation cible

## ComptaPilot (cible)

```
Accueil
Facturation → Factures, Avoirs*, Récurrentes*, Échéances*, Relances*
Paiements* → Encaissements, Rapprochement, Impayés, Remboursements
Finance → Vue, Trésorerie*, TVA, Banque, Prévisionnel*, Rapports, Clôture
Comptabilité → Propositions, Écritures, Journaux, … FEC*, Historique
Documents comptables → vue Vault filtrée
Paramètres Compta → exercice, TVA, numérotation, plan, OCR, automations*
```

\* = pas encore d’écran dédié — backlog.

### Appliqué en S1.0

- Section **Facturation** (ex Ventes)  
- **Finance** (ex Pilotage)  
- **Documents comptables**  
- **Assistant financier**  
- Badges → SalesPilot / ELFIS Core  
- Équipe / Org → `/platform/settings`

## SalesPilot (cible)

```
Accueil commercial
Relations → Prospects, Contacts, Entreprises, Clients
Pipeline → Opportunités…
Propositions → Devis, Modèles, Signature…
Catalogue → Produits, Services, Tarifs…
Activités → Tâches, Appels…
Rapports / Paramètres Sales
```

### Appliqué en S1.0

- Hint « Cycle commercial — avant facturation »  
- Liens ← ELFIS Home / ← ComptaPilot  
- Routes `/sales/*` inchangées

## ELFIS Core (cible)

```
Home, Applications, Relations*, Documents/Vault*, Communications*,
Aura*, Automatisations*, Activité, Notifications,
Organisation, Intégrations*, Paramètres ELFIS
```

### Appliqué en S1.0

- Hub `/platform/settings`  
- Home sidebar existante  
- Contrats de nav uniquement pour le reste
