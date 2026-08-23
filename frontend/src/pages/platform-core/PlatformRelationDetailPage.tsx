import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type SharedRelationDetailResponse } from '../../api'
import { useAuth } from '../../auth'
import '../../platform-workspace/platform-workspace.css'

const ROLE_LABEL: Record<string, string> = {
  customer: 'Client',
  supplier: 'Fournisseur',
  prospect: 'Prospect',
  partner: 'Partenaire',
  commercial_account: 'Compte commercial',
  employee: 'Employé',
  billing_contact: 'Contact facturation',
}

export default function PlatformRelationDetailPage() {
  const { relationId = '' } = useParams()
  const { token, orgId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState<SharedRelationDetailResponse | null>(null)

  useEffect(() => {
    if (!token || !relationId) return
    setLoading(true)
    setError('')
    api
      .getSharedRelation(token, orgId, decodeURIComponent(relationId))
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : 'Chargement impossible'))
      .finally(() => setLoading(false))
  }, [token, orgId, relationId])

  if (loading) return <div className="page panel">Chargement…</div>
  if (error) {
    return (
      <div className="page">
        <div className="panel form-error" role="alert">
          {error}
        </div>
        <Link to="/platform/relations">Retour aux relations</Link>
      </div>
    )
  }
  if (!detail) return null

  const r = detail.relation
  const addr = r.addresses[0]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <p className="muted">
            <Link to="/platform/relations">← Relations</Link>
          </p>
          <h2>{r.display_name}</h2>
          <p>
            {r.party_type} · {r.source_system}:{r.source_entity_id} · {r.status}
          </p>
        </div>
      </div>

      <section className="panel" aria-labelledby="rel-identity">
        <h3 id="rel-identity">Identité (ELFIS Core)</h3>
        <dl style={{ display: 'grid', gap: '0.45rem' }}>
          <div>
            <dt className="muted">Nom légal</dt>
            <dd>{r.legal_name || '—'}</dd>
          </div>
          <div>
            <dt className="muted">E-mails</dt>
            <dd>{r.emails.join(', ') || '—'}</dd>
          </div>
          <div>
            <dt className="muted">Téléphones</dt>
            <dd>{r.phones.join(', ') || '—'}</dd>
          </div>
          <div>
            <dt className="muted">Adresse</dt>
            <dd>
              {addr
                ? [addr.line1, addr.postal_code, addr.city, addr.country].filter(Boolean).join(', ')
                : '—'}
            </dd>
          </div>
          <div>
            <dt className="muted">TVA / SIREN / SIRET</dt>
            <dd>
              {r.tax_number || '—'} / {r.siren || '—'} / {r.siret || '—'}
            </dd>
          </div>
        </dl>
      </section>

      <section className="panel" aria-labelledby="rel-roles">
        <h3 id="rel-roles">Rôles</h3>
        <div>
          {detail.roles.map((role) => (
            <span key={role} className="platform-role-chip">
              {ROLE_LABEL[role] || role}
            </span>
          ))}
        </div>
      </section>

      <section className="panel" aria-labelledby="rel-usage">
        <h3 id="rel-usage">Utilisations</h3>
        <ul>
          <li>Finance : {detail.usages.comptapilot ? 'oui' : 'non'}</li>
          <li>Commercial : {detail.usages.salespilot ? 'oui' : 'non'}</li>
        </ul>
        <p className="muted">
          Les espaces métier s’ouvrent via Espaces — cette fiche reste dans ELFIS Core.
        </p>
      </section>

      <section className="panel" aria-labelledby="rel-dups">
        <h3 id="rel-dups">Doublons possibles</h3>
        {detail.duplicates.length === 0 ? (
          <p className="muted">Aucun signal. Aucune fusion automatique.</p>
        ) : (
          <ul>
            {detail.duplicates.map((d) => (
              <li key={`${d.left_id}-${d.right_id}`}>
                <Link to={`/platform/relations/${encodeURIComponent(d.right_id === r.id ? d.left_id : d.right_id)}`}>
                  {d.right_id === r.id ? d.left_id : d.right_id}
                </Link>
                {' — '}
                {(d.confidence * 100).toFixed(0)}% · {d.matching_fields.join(', ')}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
