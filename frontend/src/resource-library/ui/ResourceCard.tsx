import { formatEuro } from '../../api'
import { getResourceActions } from '../actions'
import type { ResourceSource } from '../sources/resourceSource'
import type { Resource, ResourceActionId } from '../types'

const KIND_LABEL: Record<Resource['kind'], string> = {
  product: 'Produit',
  service: 'Service',
  pack: 'Pack',
}

export type ResourceCardProps = {
  resource: Resource
  source: ResourceSource
  view: 'cards' | 'list'
  onAction: (action: ResourceActionId, resource: Resource) => void
}

export function ResourceCard({ resource, source, view, onAction }: ResourceCardProps) {
  const actions = getResourceActions(source, resource)
  const lastUsed =
    resource.lastUsedAt == null
      ? 'Dernière utilisation — non disponible'
      : `Dernière utilisation : ${new Date(resource.lastUsedAt).toLocaleDateString('fr-FR')}`

  return (
    <article className="sl-card" data-view={view} data-resource-id={resource.id}>
      <div>
        <div className="sl-card__top">
          <h3 className="sl-card__title">{resource.name}</h3>
          <span className="sl-card__price">{formatEuro(resource.unitPriceHt)} HT</span>
        </div>
        <div className="sl-card__meta">
          <span className="sl-badge">{KIND_LABEL[resource.kind]}</span>
          <span className="sl-badge sl-badge--muted">TVA {resource.vatRate}%</span>
          <span className={resource.status === 'active' ? 'sl-badge' : 'sl-badge sl-badge--warn'}>
            {resource.status === 'active' ? 'Actif' : 'Inactif'}
          </span>
        </div>
        {resource.description ? <p className="sl-card__desc">{resource.description}</p> : null}
        <p className="sl-card__desc">
          {resource.unit} · {lastUsed}
        </p>
      </div>
      <div className="sl-card__foot">
        <div className="sl-card__actions" role="group" aria-label={`Actions ${resource.name}`}>
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              className={action.id === 'add' || action.id === 'edit' ? 'sl-primary' : undefined}
              disabled={!action.available}
              title={action.disabledReason}
              onClick={() => onAction(action.id, resource)}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </article>
  )
}
