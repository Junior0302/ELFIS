import { HOME_APP_CARDS } from './homeCatalog'
import { HomeApplicationCard } from './HomeApplicationCard'
import { setLastProductId } from './lastProduct'

export function HomeApplicationsGrid() {
  return (
    <section className="home-apps" id="home-apps" aria-labelledby="home-apps-title">
      <div className="elfis-home__section-head">
        <h2 id="home-apps-title">Vos applications</h2>
        <p>Ouvrez un Pilot. Chaque carte porte son identité.</p>
      </div>
      <div className="home-apps__grid">
        {HOME_APP_CARDS.map((app, index) => (
          <HomeApplicationCard
            key={app.id}
            app={app}
            index={index}
            onOpen={(a) => a.productId && setLastProductId(a.productId)}
          />
        ))}
      </div>
    </section>
  )
}
