import { Container, EmptyState, PageHeader } from '../../design-system'

type SalesEmptyPageProps = {
  title: string
  description: string
}

/** Page coquille SalesPilot — aucune logique métier. */
export function SalesEmptyPage({ title, description }: SalesEmptyPageProps) {
  return (
    <Container>
      <PageHeader title={title} description={description} />
      <EmptyState
        title="Bientôt disponible"
        description="Fondation CRM SalesPilot — les écrans métier arriveront dans les prochaines phases."
      />
    </Container>
  )
}
