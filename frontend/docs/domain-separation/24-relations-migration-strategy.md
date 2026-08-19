# 24 — Relations migration strategy

## Maintenant (S1.2)

1. Lire 3 sources via adapters
2. ID opaque `source:id`
3. Doublons signalés (confidence + matching_fields)
4. Création reste dans formulaires source (Compta / Sales / contacts)
5. Exposition immédiate via adapter après création

## Plus tard (S1.3+)

1. Table `parties` + `party_roles`
2. Backfill déterministe
3. Alias ID → party_id
4. Fusion manuelle guidée (jamais auto)
5. Déprécier écritures directes identity fields dans Pilots

## Interdit

Auto-merge, suppression customer/supplier, second CRM.
