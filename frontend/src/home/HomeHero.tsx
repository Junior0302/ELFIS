import { HomeHeroVisual } from './HomeHeroVisual'

type HomeHeroProps = {
  firstName: string
}

export function HomeHero({ firstName }: HomeHeroProps) {
  return (
    <section className="home-hero" aria-labelledby="home-welcome-title">
      <div className="home-hero__copy">
        <h1 id="home-welcome-title">
          Bonjour {firstName} <span aria-hidden>👋</span>
        </h1>
        <p className="home-hero__lede">Bienvenue sur ELFIS Core.</p>
      </div>
      <HomeHeroVisual />
    </section>
  )
}
