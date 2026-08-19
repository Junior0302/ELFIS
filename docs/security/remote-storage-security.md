# Sécurité storage distant

- Pas de bucket public pour documents clients
- Service role jamais exposée au frontend
- Download par défaut via proxy ELFIS (DocumentAccessPolicy + audit)
- URL signée : TTL court, autorisation avant génération, jamais persistée / loguée
- Object keys sans PII
- Compensation ciblée (nouvel objet uniquement)
- État inconnu après timeout → anomalie / orphan, pas « absent » automatique
- Legal hold inchangé avant purge distante
