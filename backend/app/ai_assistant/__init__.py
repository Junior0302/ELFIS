"""AI Financial Assistant V1 — copilote financier ELFIS Core.

Le LLM n'est jamais la source de vérité.
Toutes les données proviennent des moteurs internes (Financial, Banking,
Accounting, Billing, Search, Vault) via des outils contrôlés.

Le Decision Engine est le seul point d'entrée conversationnel :
récupération → contexte → outils → LLM (explication) → validation → formatage.
"""
