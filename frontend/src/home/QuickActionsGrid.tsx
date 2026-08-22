import { WORKSPACE_ACCENTS } from '../workspaces'
import { PlatformActionItem } from './PlatformActionItem'
import { PlatformHomeSection } from './PlatformHomeSection'

/**
 * Actions rapides — routes SPA existantes + label d’espace.
 * Deposit comptable = Finance ; Vault = Documents.
 */
export const HOME_QUICK_ACTIONS = [
  {
    id: 'facture',
    title: 'Facture',
    description: 'Créer une facture',
    href: '/facturation/documents/new',
    workspaceLabel: 'Finance',
    accent: WORKSPACE_ACCENTS.finance.primary,
  },
  {
    id: 'devis',
    title: 'Devis',
    description: 'Ouvrir les devis',
    href: '/devis',
    workspaceLabel: 'Finance',
    accent: WORKSPACE_ACCENTS.finance.primary,
  },
  {
    id: 'prospect',
    title: 'Prospect',
    description: 'Créer / voir les leads',
    href: '/sales/leads',
    workspaceLabel: 'Commercial',
    accent: WORKSPACE_ACCENTS.commercial.primary,
  },
  {
    id: 'import-doc',
    title: 'Document',
    description: 'Déposer dans le coffre',
    href: '/platform/documents',
    workspaceLabel: 'Documents',
    accent: WORKSPACE_ACCENTS.documents.primary,
  },
  {
    id: 'tache',
    title: 'Tâche',
    description: 'File de travail',
    href: '/work-queue',
    workspaceLabel: 'Plateforme',
    accent: undefined,
  },
  {
    id: 'relation',
    title: 'Relation',
    description: 'Relations entreprise',
    href: '/platform/relations',
    workspaceLabel: 'Plateforme',
    accent: undefined,
  },
] as const

type QuickActionsGridProps = {
  embedded?: boolean
}

export function QuickActionsGrid({ embedded = false }: QuickActionsGridProps) {
  return (
    <PlatformHomeSection
      id="home-quick"
      title="Actions rapides"
      description="Gestes transverses — l’espace cible est indiqué."
      level={3}
      className={`cockpit-quick ph-quick ${embedded ? 'cockpit-quick--embedded' : ''}`.trim()}
    >
      <div className="ph-quick__grid" data-cockpit-quick="v1">
        {HOME_QUICK_ACTIONS.map((action) => (
          <PlatformActionItem
            key={action.id}
            title={action.title}
            description={action.description}
            href={action.href}
            workspaceLabel={action.workspaceLabel}
            accent={'accent' in action ? action.accent : undefined}
          />
        ))}
      </div>
    </PlatformHomeSection>
  )
}
