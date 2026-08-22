import { Container, EmptyState, PageHeader } from '../../design-system'

type SalesEmptyPageProps = {
  title: string
  description: string
}

/** Page coquille Commercial — aucune logique métier. */
export function SalesEmptyPage({ title, description }: SalesEmptyPageProps) {
  return (
    <Container>
      <PageHeader eyebrow="Commercial" title={title} description={description} />
      <EmptyState
        title="Bientôt disponible"
        description="Cet écran Commercial n’est pas encore disponible."
      />
    </Container>
  )
}
