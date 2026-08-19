# 01 — Experience Principles

**P1.1** · ELFIS Core Platform Experience  
Aligné Brand Book : Connected Ecosystem · Platform ≠ Product.

---

## Mission UX

```
Utilisateur → entre dans ELFIS Core (plateforme)
           → choisit un Pilot (expertise)
           → travaille sans perdre le fil plateforme
           → bascule vers un autre Pilot sans rupture d’identité
```

---

## 8 principes

| # | Principe | Règle courte |
|---|----------|--------------|
| 1 | **Plateforme d’abord** | Topbar / launcher / search / notif / profil = ELFIS Core |
| 2 | **Un Pilot à la fois** | Un Product Shell actif ; primary = Pilot courant |
| 3 | **Mark stable** | Changement de Pilot = couleur + wordmark, pas nouveau symbole |
| 4 | **Une intention / écran** | Pas de widgets concurrentiels dans le chrome |
| 5 | **Continuité** | Org, user, notifs persistent cross-Pilot |
| 6 | **Découvrabilité** | Launcher = porte d’entrée famille ; search = raccourci |
| 7 | **Densité contextuelle** | Public / chrome aéré ; workspace métier plus dense |
| 8 | **Prévisibilité** | Mêmes emplacements chrome sur tous les Pilot |

---

## Hiérarchie d’attention

```
1. Contenu métier (workspace)
2. Nav produit (sidebar Pilot)
3. Chrome plateforme (topbar)
4. Overlays (launcher, search, notif, profil)
```

---

## Do / Don’t

```
DO                              DON’T
─────────────────────────────   ─────────────────────────────
Launcher = composant plateforme  Launcher dans sidebar Pilot
Org + user toujours visibles     Re-login à chaque Pilot
Search globale cross-Pilot       10 barres de search locales
Notifs unifiées                  Boîtes cloisonnées opaques
Signature by ELFIS sur Pilot     Produit qui « mange » la topbar
```

---

## États plateforme

```
┌─────────────┐
│ Anonymous   │  Landing / Login
└──────┬──────┘
       ▼
┌─────────────┐
│ Authenticated│  Platform Shell ON
└──────┬──────┘
       ▼
┌─────────────┐     ┌──────────────┐
│ Org selected│ ──► │ Pilot active │
└─────────────┘     └──────────────┘
```

---

## Critères de succès UX

- [ ] Utilisateur nomme le Pilot actif en < 2 s  
- [ ] Basculer Compta → Sales < 3 clics / 1 raccourci  
- [ ] Retrouver org / profil sans quitter le chrome  
- [ ] Aucune confusion « suis-je dans ELFIS ou dans une app isolée ? »
