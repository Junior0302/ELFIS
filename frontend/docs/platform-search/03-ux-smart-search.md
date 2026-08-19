# 03 — UX Smart Search

## Composants

- `SmartSearch` — combobox (`role=combobox` / `listbox` / `option`)
- Résultats groupés (`SmartSearchGroupView`)
- États : idle / typing / loading / ready / empty / error / offline / partial

## Comportement

- Debounce **280 ms** (aligné Command Center)
- Min **2** caractères en scope global ; pickers peuvent `allowEmptyQuery`
- AbortController + ignore réponses périmées
- Cache court **8 s** par clé (q+scope+types+org)

## Design

Tokens `--pilot-accent`, `--pilot-focus`, `--pilot-border` via `platform-search.css`.

## Récents

Contrat `RecentsProvider` / `FavoritesProvider` exposé ; **enabled: false** tant qu’aucune source métier permanente (pas de localStorage métier).
