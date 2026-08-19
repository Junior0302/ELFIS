# Sécurité — product document integration

- Isolation tenant sur packages / deliveries / issues
- Pas de montants, noms, OCR, payloads dans audit
- Pas d’object_key / URL / token exposés
- Quarantaine : pas de validation normale ni package ni publication
- Legal hold : bloque purge artefacts ; ne force pas une livraison
- Bridge désactivé ≠ panne health
- Worker livraisons hors processus API production
