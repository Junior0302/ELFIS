"""Banking Platform V1 — moteur bancaire indépendant des fournisseurs.

Architecture :
- Banking Engine   : source de vérité (banques, comptes, soldes, transactions)
- Connector Layer  : interface commune ``BankConnector`` (demo, bridge, powens…)
- Sync Engine      : import initial, incrémental, doublons, retry, reprise
- Health           : état des connexions et des fournisseurs

Aucun code métier ne doit importer un connecteur fournisseur directement :
tout passe par ``app.banking.connectors.registry`` et ``BankingEngine``.
"""
