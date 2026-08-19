/**
 * Placeholder import — emplacements CSV + InventoryPilot, pas d’implémentation.
 */

export type ImportPlaceholderProps = {
  onClose: () => void
}

export function ImportPlaceholder({ onClose }: ImportPlaceholderProps) {
  return (
    <div className="sl-import" role="dialog" aria-label="Importer des ressources">
      <h3 style={{ margin: '0 0 0.35rem' }}>Importer</h3>
      <p className="sl-status" style={{ margin: 0 }}>
        L’import n’est pas implémenté en F1.2. Emplacements prévus :
      </p>
      <ul>
        <li>
          <strong>CSV bibliothèque locale</strong> — mapping colonnes nom / type / prix HT / TVA /
          unité (à venir).
        </li>
        <li>
          <strong>InventoryPilot</strong> — synchronisation catalogue owner Inventory (placeholder —
          Pilot non branché).
        </li>
      </ul>
      <div className="sl-form__actions" style={{ marginTop: '0.85rem' }}>
        <button type="button" className="btn secondary" disabled title="Non implémenté">
          Choisir un fichier CSV
        </button>
        <button type="button" className="btn secondary" disabled title="InventoryPilot indisponible">
          Depuis InventoryPilot
        </button>
        <button type="button" className="btn" onClick={onClose}>
          Fermer
        </button>
      </div>
    </div>
  )
}
