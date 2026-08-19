import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type BillingOverview } from '../../api'
import { useAuth } from '../../auth'
import '../../comptapilot/facturation/facturation-premium.css'
import '../../comptapilot/facturation/facturation-spaces.css'

const LINKS = [
  {
    to: '/facturation/documents',
    title: 'Documents',
    desc: 'Liste, édition et suivi des documents commerciaux.',
  },
  {
    to: '/catalogue',
    title: 'Catalogue',
    desc: 'Produits et prestations pour vos documents.',
  },
  {
    to: '/activites',
    title: 'Activité',
    desc: 'Activités commerciales liées à la facturation.',
  },
] as const

export default function FacturationOverviewPage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<BillingOverview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    let cancelled = false
    api
      .billingOverview(token, orgId)
      .then((payload) => {
        if (!cancelled) setData(payload)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Erreur chargement')
      })
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  return (
    <div className="billing-page" data-billing-layout="fp05" data-fp-space="overview">
      <header className="fp-header">
        <div className="fp-header__intro">
          <h2>Facturation</h2>
          <p className="fp-header__lede">
            Vue d’ensemble des documents commerciaux. Créez un document depuis Documents.
          </p>
          <div className="fp-header__meta" aria-label="Métadonnées facturation">
            <span className="fp-chip">ComptaPilot</span>
            {data?.smtp_configured != null ? (
              <span className="fp-chip">
                SMTP {data.smtp_configured ? 'configuré' : 'non configuré'}
              </span>
            ) : null}
          </div>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}

      <section className="fp-section" aria-labelledby="fp-overview-kpi">
        <h3 className="fp-section__title" id="fp-overview-kpi">
          Essentiel
        </h3>
        {!data ? (
          <p className="muted">Chargement des indicateurs…</p>
        ) : (
          <div className="fp-kpi-grid">
            <div className="fp-kpi">
              <span className="fp-kpi__label">Documents</span>
              <strong className="fp-kpi__value">{data.stats.documents}</strong>
            </div>
            <div className="fp-kpi">
              <span className="fp-kpi__label">Clients</span>
              <strong className="fp-kpi__value">{data.stats.customers}</strong>
            </div>
            <div className="fp-kpi fp-kpi--alert">
              <span className="fp-kpi__label">Impayés</span>
              <strong className="fp-kpi__value">{data.stats.unpaid}</strong>
            </div>
            <div className="fp-kpi fp-kpi--emphasis">
              <span className="fp-kpi__label">Montant dû</span>
              <strong className="fp-kpi__value">{formatEuro(data.stats.unpaid_amount)}</strong>
            </div>
          </div>
        )}
      </section>

      <section className="fp-section" aria-labelledby="fp-overview-spaces">
        <h3 className="fp-section__title" id="fp-overview-spaces">
          Espaces
        </h3>
        <div className="fp-overview-cards">
          {LINKS.map((link) => (
            <Link key={link.to} to={link.to} className="fp-overview-card">
              <strong>{link.title}</strong>
              <span>{link.desc}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="fp-section" aria-labelledby="fp-overview-legacy">
        <h3 className="fp-section__title" id="fp-overview-legacy">
          Accès rapides
        </h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Les routes historiques restent disponibles :{' '}
          <Link to="/facturation/documents">documents & CRUD</Link>, <Link to="/devis">devis</Link>,{' '}
          <Link to="/clients">clients</Link>,{' '}
          <Link to="/platform/relations?tab=customer">ELFIS Relations</Link>.
        </p>
      </section>
    </div>
  )
}
