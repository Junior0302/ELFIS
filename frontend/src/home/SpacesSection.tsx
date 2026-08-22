import { PlatformHomeSection } from './PlatformHomeSection'
import { PlatformSpaceCard } from './PlatformSpaceCard'
import { resolveSpaceSummaries } from './homeSignals'

type SpacesSectionProps = {
  lastProductId: string | null
  lastProductAt: string | null
}

/** Vos espaces — cartes registry (même SoT que Espaces). */
export function SpacesSection({ lastProductId, lastProductAt }: SpacesSectionProps) {
  const spaces = resolveSpaceSummaries(lastProductId, lastProductAt)

  return (
    <PlatformHomeSection
      id="home-spaces"
      title="Retrouvez tous les espaces de votre entreprise."
      description="Accédez à vos métiers depuis un environnement ELFIS unique."
      level={3}
      className="ph-spaces"
    >
      <div className="ph-spaces__grid" data-cockpit-spaces="v1">
        {spaces.map((space) => (
          <PlatformSpaceCard
            key={space.id}
            id={space.id}
            title={space.title}
            description={space.summary}
            icon={space.icon}
            engineLabel={space.poweredBy ?? undefined}
            statusLabel={space.statusLabel}
            accent={space.accent}
            accentSoft={space.accentSoft}
            available={space.available}
            to={space.to}
            engineProductId={space.productId}
            resumeHint={space.resumeHint}
          />
        ))}
      </div>
    </PlatformHomeSection>
  )
}
