import type { CSSProperties } from 'react'
import { HOME_TIMELINE_MOCK } from './homeCatalog'

export function RecentActivityPanel() {
  const todayItems = HOME_TIMELINE_MOCK.filter((i) => i.day === 'today')
  const yesterdayItems = HOME_TIMELINE_MOCK.filter((i) => i.day === 'yesterday')

  return (
    <section
      className="home-activity"
      id="home-activity"
      aria-labelledby="home-activity-title"
    >
      <div className="elfis-home__section-head">
        <h2 id="home-activity-title">Activité récente</h2>
        <p className="elfis-home__mock-badge">Aperçu</p>
      </div>
      <div className="home-timeline" role="list">
        <div className="home-timeline__day">
          <h3>Aujourd&apos;hui</h3>
          <ol className="home-timeline__list">
            {todayItems.map((item, i) => (
              <li key={item.id} style={{ '--tl-delay': `${i * 50}ms` } as CSSProperties}>
                <span className="home-timeline__dot" aria-hidden />
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.detail}</span>
                  <time>{item.at}</time>
                </div>
              </li>
            ))}
          </ol>
        </div>
        <div className="home-timeline__day">
          <h3>Hier</h3>
          <ol className="home-timeline__list">
            {yesterdayItems.map((item, i) => (
              <li
                key={item.id}
                style={{ '--tl-delay': `${(todayItems.length + i) * 50}ms` } as CSSProperties}
              >
                <span className="home-timeline__dot" aria-hidden />
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.detail}</span>
                  <time>{item.at}</time>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
      <a className="home-activity__all" href="#home-activity">
        Voir toute l&apos;activité
      </a>
      <p className="elfis-home__mock-hint">Chronologie illustrative (aperçu).</p>
    </section>
  )
}
