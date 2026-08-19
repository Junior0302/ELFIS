import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { getProductById } from '../design-system'
import { ProductMark } from '../app-launcher/ProductMark'
import { cx } from '../design-system'
import type { HomeAppCard } from './homeCatalog'

type HomeApplicationCardProps = {
  app: HomeAppCard
  onOpen?: (app: HomeAppCard) => void
  index?: number
}

export function HomeApplicationCard({ app, onOpen, index = 0 }: HomeApplicationCardProps) {
  const product = app.productId ? getProductById(app.productId) : null
  const style = {
    '--home-app-accent': app.accent,
    '--home-card-delay': `${Math.min(index, 5) * 40}ms`,
  } as CSSProperties

  const body = (
    <>
      <span className="home-app-card__top">
        <span className="home-app-card__mark">
          {product ? (
            <ProductMark product={product} size="md" />
          ) : (
            <span className="home-app-card__initial" aria-hidden>
              {app.name.charAt(0)}
            </span>
          )}
        </span>
        <span className={cx('home-app-card__status', !app.available && 'is-soon')}>
          {app.statusLabel}
        </span>
      </span>
      <span className="home-app-card__body">
        <strong className="home-app-card__name">{app.name}</strong>
        <span className="home-app-card__desc">{app.description}</span>
        <ul className="home-app-card__caps" aria-label={`Capacités ${app.name}`}>
          {app.capabilities.map((cap) => (
            <li key={cap}>{cap}</li>
          ))}
        </ul>
      </span>
      {app.available && app.to ? (
        <span className="home-app-card__cta">Ouvrir</span>
      ) : (
        <span className="home-app-card__cta is-muted">Bientôt</span>
      )}
    </>
  )

  if (!app.available || !app.to) {
    return (
      <div
        className={cx('home-app-card', 'is-disabled', `home-app-card--${app.id}`)}
        style={style}
        aria-disabled="true"
      >
        {body}
      </div>
    )
  }

  return (
    <Link
      to={app.to}
      className={cx('home-app-card', `home-app-card--${app.id}`)}
      style={style}
      onClick={() => onOpen?.(app)}
    >
      {body}
    </Link>
  )
}

/** @deprecated Prefer HomeApplicationCard */
export { HomeApplicationCard as HomeAppCardView }
