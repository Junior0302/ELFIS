# 07 — Platform Governance

**P3.0.1** · Contrat officiel.  
Règles d’entrée d’un **nouveau Pilot** sur la plateforme ELFIS.

---

## Principe

```
Aucun Pilot n’est « branché » sans passer la checklist.
GO seulement si tous les items critiques sont verts.
```

Alignement : Orchestrator coordonne · Pilot exécute · ownership unique · events `objet.action` · Intent via Command Center.

---

## Processus d’onboarding (conceptuel)

```
1. Déclaration mission + domaines
2. Ownership Model (pas de conflit)
3. Capability Registry
4. Event Naming
5. Permissions Pilot
6. Search / Command Center / Launcher
7. Theme / Brand
8. Branchement Orchestrator + Knowledge Graph
9. Revue GO / NO GO
10. Publication contrats Pilot
```

---

## Checklist d’intégration

| # | Domaine | Exigence | Critique |
|---|---------|----------|----------|
| 1 | **Capability Registry** | Toutes capabilities documentées (owner, prérequis, permissions, events, résultat) | Oui |
| 2 | **Event Naming** | Events en `objet.action` ; pas d’alias sauvages | Oui |
| 3 | **Ownership** | Domaines listés ; aucun chevauchement non résolu | Oui |
| 4 | **Permissions** | Droits par capability ; refus non contournable | Oui |
| 5 | **Search** | Entités indexables déclarées ; owner index ≠ métier | Oui |
| 6 | **Command Center** | Intents → capabilities / navigation documentées | Oui |
| 7 | **Launcher** | Entrée produit déclarée (identité Pilot) | Oui |
| 8 | **Theme** | Respect chrome / tokens plateforme (pas de fork UI sauvage) | Recommandé |
| 9 | **Brand** | Nom, mission, présence cohérente ELFIS | Recommandé |
| 10 | **Orchestrator** | Pas d’intégration Pilot↔Pilot hors hub ; workflows déclarés | Oui |
| 11 | **Knowledge Graph** | Relations / refs documentées ; pas de dump métier | Oui |

---

## Matrice GO / NO GO

| Critère | GO | NO GO |
|---------|----|-------|
| Owner unique par domaine | Clair et signé | Deux owners ou ambiguïté |
| Capabilities publiées | Registry complet | Actions « cachées » |
| Events conformes | `objet.action` | `InvoiceCreated`, fourre-tout |
| Permissions | Matrice capability × droit | Actions sans authz |
| Pas de logique métier dans Orchestrator | Respecté | Hub qui « fait la TVA » |
| Pas de sync directe Pilot↔Pilot | Via Orchestrator / events | Hooks N×N |
| Search | Contrat index déclaré | Index = copie métier divergente |
| Command Center | Intents mappées | Appels capability UI directs cross-Pilot |
| Knowledge Graph | Liens refs seulement | Graphe = entrepôt métier |
| Payload | Principes P1–P8 | Dump / secrets / instructions |
| Brand / Launcher / Theme | Présence minimale OK | Hors grille / chrome cassé *(bloquant si UX plateforme cassée)* |

```
          ┌─────────────┐
          │  Checklist  │
          └──────┬──────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
      GO                 NO GO
  intégration         correction
  autorisée           obligatoire
```

---

## Qui valide quoi (conceptuel)

| Sujet | Responsable typique |
|-------|---------------------|
| Ownership & domaines | Gouvernance plateforme |
| Capabilities & events | Owner Pilot + revue plateforme |
| Permissions | Owner Pilot + sécurité plateforme |
| Search / CC / Launcher | Plateforme (shell) |
| Orchestrator / workflows | Plateforme Orchestrator |
| Knowledge Graph | Plateforme graphe + owners concernés |
| Theme / Brand | Design système / brand book |

---

## Évolution des contrats

| Changement | Règle |
|------------|-------|
| Nouvelle capability | Ajout registry + permissions + events |
| Nouvel event | Conformité naming + listeners documentés |
| Nouveau domaine de données | Ownership avant code |
| Dépréciation event / capability | Fenêtre + successeur (voir 03) |
| Divergence vision Orchestrator vs contrat | **Le contrat gagne** |

---

## Interdits absolus à l’entrée

| Interdit |
|----------|
| Brancher un Pilot sans Capability Registry |
| Inventer un second owner « temporaire » |
| Intégration directe Pilot↔Pilot pour le cross-produit |
| Events hors convention `objet.action` |
| Stocker le métier dans Orchestrator ou Knowledge Graph |
| Contournement permissions via workflow |
| Démarrer P3.1 / implémentation sous prétexte d’onboarding doc |

---

## Résumé GO

Un Pilot est **GO** si et seulement si :

1. Ownership sans conflit  
2. Capabilities + Events + Permissions publiés  
3. Intent / CC / Search / Launcher alignés  
4. Orchestrator = seul hub cross-produit  
5. Knowledge Graph = refs uniquement  
6. Checklist critique entièrement verte  
