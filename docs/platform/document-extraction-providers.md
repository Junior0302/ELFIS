# Providers d'extraction (RC2.5.4)

## Contrat

`DocumentExtractionProvider.extract(ExtractionRequest) → ExtractionProviderResult`  
N'écrit ni en DB ni Storage ; n'appelle aucune route ; n'accède à aucun secret inutile.

## Providers

| key | Rôle |
|-----|------|
| `noop` | Tests / staging — modes ok/partial/invalid/retryable/permanent/timeout |
| `rules` | Regex bornées déterministes (dates, montants FR/EN, devises, labels) |

`external` / OpenAI / IA → refusés.  
Scores = **heuristiques**, pas des probabilités scientifiques.

## Limites rules

- Regex non catastrophiques, scan tronqué  
- Timeout / max caractères  
- Aucun réseau / ML  
- Preuves : page + rule + evidence_code — **pas** d'extraits texte longs
