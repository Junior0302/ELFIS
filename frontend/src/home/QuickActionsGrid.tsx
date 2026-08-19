import { QuickActionCard } from '../design-system'
import { GridItem, PlatformGrid } from '../unified-platform'

/** Routes existantes uniquement — pas de faux liens. */
export const HOME_QUICK_ACTIONS = [
  {
    id: 'facture',
    title: 'Facture',
    description: 'Composer une facture',
    href: '/facturation/documents/new',
  },
  {
    id: 'devis',
    title: 'Devis',
    description: 'Ouvrir les devis',
    href: '/devis',
  },
  {
    id: 'prospect',
    title: 'Prospect',
    description: 'Leads commerciaux',
    href: '/sales/leads',
  },
  {
    id: 'import-doc',
    title: 'Import doc',
    description: 'Déposer un document',
    href: '/deposit',
  },
  {
    id: 'tache',
    title: 'Tâche',
    description: 'File de travail',
    href: '/work-queue',
  },
  {
    id: 'relation',
    title: 'Relation',
    description: 'Relations plateforme',
    href: '/platform/relations',
  },
] as const

type QuickActionsGridProps = {
  embedded?: boolean
}

export function QuickActionsGrid({ embedded = false }: QuickActionsGridProps) {
  return (
    <section
      className={`cockpit-quick ${embedded ? 'cockpit-quick--embedded' : ''}`.trim()}
      id="home-quick"
      aria-labelledby="home-quick-title"
      data-cockpit-quick="v1"
    >
      <div className="elfis-home__section-head elfis-home__section-head--compact">
        <h2 id="home-quick-title">Quick Actions</h2>
        <p>Gestes OS — routes existantes.</p>
      </div>
      <PlatformGrid columns={12} gap={3} className="cockpit-quick__grid">
        {HOME_QUICK_ACTIONS.map((action) => (
          <GridItem key={action.id} span={6} spanMd={4} spanLg={2}>
            <QuickActionCard
              title={action.title}
              description={action.description}
              href={action.href}
              compact
              accent={false}
              className="cockpit-quick__card"
            />
          </GridItem>
        ))}
      </PlatformGrid>
    </section>
  )
}
