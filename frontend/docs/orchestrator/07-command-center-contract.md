# 07 — Contrat Command Center ↔ Orchestrator

**P3.0** · Comment le Command Center dialogue avec l’Orchestrator.  
Réf. plateforme : `frontend/docs/platform/command-center-v1.md` (UX actuelle : search + navigation ; **pas** d’exécution métier aujourd’hui).

---

## Rôles

| Composant | Rôle |
|-----------|------|
| **Command Center (CC)** | Surface UX : rechercher, naviguer, exprimer une intention |
| **Search Engine** | Source de vérité des hits indexés (inchangé) |
| **Orchestrator** | Résout l’intention → Pilot / workflow / droits |
| **Pilot** | Exécute |

```
┌─────────────┐     intention      ┌──────────────┐     action     ┌───────┐
│ Command     │ ─────────────────► │ Orchestrator │ ─────────────► │ Pilot │
│ Center      │ ◄── résultat UX ── │              │ ◄── outcome ── │       │
└─────────────┘                    └──────────────┘                └───────┘
       │
       └── search hits ──► Search Engine (lecture seule index)
```

Le CC **ne parle pas métier** directement aux Pilots pour les commandes cross-produit.

---

## Types d’intentions CC

| Type | Exemple | Traitement |
|------|---------|------------|
| Navigation | Ouvrir SalesPilot | Route / Launcher (peut rester local) |
| Recherche entité | Trouver facture X | Search Engine → deep-link |
| Commande simple | Créer une facture | Orchestrator → action Pilot |
| Commande workflow | « Clôturer prospect gagné » | Orchestrator → workflow |
| (Futur) Langage naturel | Phrase libre | Couche IA → intentions structurées |

P3.0 documente le **contrat** ; l’implémentation des commandes métier via Orchestrator est roadmap (voir 09).

---

## Exemple — Créer une facture

```
Utilisateur
    │  tape / choisit « Créer une facture »
    ▼
Command Center
    │  intention: compta.invoice.create
    ▼
Orchestrator
    │  1. capability known?
    │  2. user has compta.invoice.create?
    │  3. org context ok?
    ▼
ComptaPilot
    │  validation métier + création (ou ouverture UI guidée)
    ▼
Résultat
    ├─ succès → navigation facture + event invoice.created
    ├─ denied → message droits dans CC
    └─ failed → erreur actionnable
```

---

## Exemple — Ouvrir une entité trouvée

```
User → CC → Search Engine (hit)
              │
              ▼
         deep-link Pilot
         (Orchestrator non requis si lecture pure)
```

Orchestrator intervient si l’ouverture déclenche une **action** ou un **workflow**, pas pour la simple navigation.

---

## Contrat d’échange (conceptuel)

### CC → Orchestrator

| Champ | Description |
|-------|-------------|
| `intention` | Identifiant stable (`compta.invoice.create`) |
| `actorId` | Utilisateur courant |
| `orgId` | Organisation active |
| `params` | Paramètres saisis / contexte |
| `source` | `command_center` |
| `correlationId` | Pour audit |

### Orchestrator → CC

| Champ | Description |
|-------|-------------|
| `status` | `ok` / `denied` / `needs_input` / `failed` |
| `resultRef` | Lien entité / route |
| `message` | Texte UX |
| `validationRequired?` | Gate humaine |

---

## Évolution vers l’IA (conceptuel uniquement)

```
V1–V2 : intentions explicites (menus, mode `>`, keywords)
V3    : automations déclenchées sans passer par le CC
V4    : CC reformule le langage naturel → intentions structurées
V5    : agents supervisés proposent des workflows ; humain valide
```

L’IA **ne remplace pas** Orchestrator ni les Pilots : elle propose des intentions qui empruntent le **même contrat** (droits, audit, gates).

```
User NL → (futur) AI Interpreter → Intention structurée → Orchestrator → Pilot
                                      │
                                      └── mêmes permissions que les commandes manuelles
```

---

## Frontières avec le CC actuel (P2.4)

| Aujourd’hui (livré) | Cible Orchestrator |
|---------------------|--------------------|
| Search + nav + suggestions locales | + commandes routées Orchestrator |
| Mode `>` = navigation | Mode `>` = intentions + exécution autorisée |
| Pas de logique métier Compta/Sales dans le CC | Toujours vrai — métier reste Pilot |
| Interdit : Workflow/IA dans le CC seul | Workflows vivent dans Orchestrator |

Le CC reste une **porte d’entrée** ; l’Orchestrator est la **salle des machines**.
