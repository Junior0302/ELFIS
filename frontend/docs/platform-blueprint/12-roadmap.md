# 12 — Roadmap architecture (post-P0)

**ELFIS Platform Blueprint V1**

> Roadmap **d’architecture et de gouvernance** — pas un plan d’implémentation daté au sprint près.  
> Aucune date commerciale irréaliste n’est inventée ici.

---

## Statut P0

| Livrable | État |
|----------|------|
| Platform Blueprint V1 (ce dossier) | **Terminé (phase documentaire)** |
| Développement fonctionnel dans P0 | Non démarré (interdit) |

**Phase P0 terminée** → les chantiers produit reportés peuvent **reprendre** hors de cette phase.

---

## Reprise immédiate possible (hors P0)

| Chantier | Note |
|----------|------|
| **Facturation Premium** | **F1.0 livré** (workflow foundation) — docs [`../facturation-premium/`](../facturation-premium/README.md). F1.1 non démarré. |
| Améliorations ComptaPilot commerciales | Selon audits commercial-readiness déjà produits |
| Financial Command Center / Dashboard Premium | Continuité des docs & UI déjà engagés |

---

## Suites architecture déjà identifiées dans le repo

| Suite | Nature | Commentaire |
|-------|--------|-------------|
| **S1.3 Relations** | Party unifié / fusion tables / dédoublonnage | **Suite future** — hors P0 ; S1.2 reste en projection / contrat |
| Renforcement capacités Inventory / Banking | Ownership cible Blueprint | Quand le produit mature ; pas de création de Pilot dans P0 |
| Orchestrator & platform-contracts | Continuité | Intents, events, ownership |
| Expérience plateforme (shell, search, notifs) | Continuité | [`../platform/`](../platform/README.md) |
| **Smart Search & Universal Pickers (P1.0)** | Capacité Core livrée | [`../platform-search/`](../platform-search/README.md) |
| **ELFIS Resource System / Smart Library (F1.2)** | Capacité Core livrée | [`../resource-library/`](../resource-library/README.md) |
| **ELFIS Insight Framework (F1.2.5)** | Capacité Core livrée | [`../insight-framework/`](../insight-framework/README.md) |
| **Live Document Experience (F1.3)** | Assemblage UX Composer | [`../live-document/`](../live-document/README.md) — **livré** ; F1.4 **non démarré** |
| Aura plateforme | Continuité migration / positionnement couche 3 | Pas un Pilot |

Réf. domain-separation (hors scope S1.2 explicite) : [`../domain-separation/README.md`](../domain-separation/README.md)

---

## Ordre de priorité architectural recommandé

```
1. Respecter le Blueprint sur tout nouveau chantier
2. Facturation Premium **F1.0** (espaces + wizard) — F1.1 ensuite
3. Faire évoluer Relations (S1.3+) sans casser Zero ressaisie
4. Exposer des capacités Inventory / Banking au fil de la maturité
5. Enrichir Aura sur signaux stables (pas sur données fantômes)
```

---

## Ce que cette roadmap n’est pas

- Un engagement de dates (trimestre X, mois Y)
- Une autorisation à créer de nouveaux Pilots « pour la démo »
- Un substitut aux backlogs produit détaillés (commercial-readiness, FCC, etc.)

---

## Synthèse

> **P0 = fondation documentaire officielle.**  
> **Ensuite :** Facturation Premium peut reprendre ; S1.3 Relations reste une suite future.  
> Toute suite reste soumise aux Trois Lois, Zero ressaisie et Zero verrou.
