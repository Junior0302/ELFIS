# 08 — Clavier & raccourcis

| Touche | Comportement (SmartSearch / pickers) |
|--------|--------------------------------------|
| ↑ / ↓ | Navigation options |
| Enter | Sélection active |
| Escape | Ferme panneau |
| Tab | Sortie naturelle (pas de preventDefault) |

## Cmd/Ctrl+K

**Owner exclusif** : `platform-command/CommandCenter` (`GLOBAL_SHORTCUT_OWNER`).

P1.0 n’enregistre **aucun** listener global concurrent. Intégration légère Command Center optionnelle = **reportée** (documentée ci-dessous).

### Intégration CC optionnelle (future)

Réutiliser `SearchResult` adapters pour enrichir l’affichage des hits Engine — sans réécrire le CC ni dupliquer le raccourci.
