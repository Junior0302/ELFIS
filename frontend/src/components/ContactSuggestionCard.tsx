import { useMemo, useState, type FormEvent } from 'react'
import {
  api,
  type ContactExtractedData,
  type ContactSuggestion,
} from '../api'

type Props = {
  documentId: number
  suggestion: ContactSuggestion
  token: string
  orgId?: number | null
  onResolved: () => void
  onMessage: (msg: string) => void
}

function roleLabel(role: string, contactType: string) {
  if (contactType === 'prospect') return 'prospect'
  if (role === 'supplier') return 'fournisseur'
  return 'client'
}

function formatSiret(value?: string | null) {
  const d = (value || '').replace(/\D/g, '')
  if (d.length !== 14) return value || '—'
  return `${d.slice(0, 3)} ${d.slice(3, 6)} ${d.slice(6, 9)} ${d.slice(9)}`
}

export default function ContactSuggestionCard({
  documentId,
  suggestion,
  token,
  orgId,
  onResolved,
  onMessage,
}: Props) {
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<ContactExtractedData>({
    ...suggestion.extracted_data,
  })

  const title = useMemo(() => {
    const label = roleLabel(suggestion.role, suggestion.suggested_contact_type)
    if (suggestion.suggested_action === 'create_contact') {
      return `Nouveau ${label} détecté`
    }
    if (suggestion.suggested_action === 'link_existing_contact') {
      return `${label.charAt(0).toUpperCase()}${label.slice(1)} reconnu`
    }
    if (suggestion.suggested_action === 'review_possible_duplicate') {
      return `Un ${label} similaire existe déjà`
    }
    if (suggestion.suggested_action === 'enrich_existing_contact') {
      return 'De nouvelles informations ont été détectées'
    }
    return 'Suggestion de contact'
  }, [suggestion])

  const company =
    form.company_name ||
    suggestion.extracted_data.company_name ||
    'Contact sans nom'
  const topDup = suggestion.possible_duplicates?.[0]

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    try {
      await fn()
      onResolved()
    } catch (err) {
      onMessage(err instanceof Error ? err.message : 'Action impossible')
    } finally {
      setBusy(false)
    }
  }

  const onCreate = (e?: FormEvent) => {
    e?.preventDefault()
    void run(async () => {
      await api.createContactFromDocument(
        {
          document_id: documentId,
          role: suggestion.role,
          contact_type: suggestion.suggested_contact_type,
          suggestion_id: suggestion.id,
          confirmed_data: form,
        },
        token,
        orgId,
      )
      onMessage('Contact enregistré et associé au document.')
    })
  }

  const onLink = (contactId?: number | null) => {
    const id = contactId || suggestion.matched_contact_id
    if (!id) {
      onMessage('Aucun contact à associer.')
      return
    }
    void run(async () => {
      await api.linkDocumentContact(
        documentId,
        { contact_id: id, role: suggestion.role, suggestion_id: suggestion.id },
        token,
        orgId,
      )
      onMessage('Document associé au contact existant.')
    })
  }

  const onIgnore = () => {
    void run(async () => {
      await api.ignoreContactSuggestion(
        documentId,
        { role: suggestion.role, suggestion_id: suggestion.id },
        token,
        orgId,
      )
      onMessage('Suggestion ignorée.')
    })
  }

  const onEnrich = () => {
    const fields = Object.keys(suggestion.new_fields || {}).filter(
      (k) => k !== 'iban_conflict',
    )
    const hasIbanConflict = Boolean(suggestion.new_fields?.iban_conflict)
    if (hasIbanConflict && !fields.includes('iban')) {
      // IBAN conflict requires explicit confirm
    }
    void run(async () => {
      const accepted = [...fields]
      const fieldValues: Record<string, string> = { ...suggestion.new_fields }
      if (suggestion.new_fields?.iban_conflict) {
        accepted.push('iban')
        fieldValues.iban = String(suggestion.new_fields.iban_conflict)
      }
      await api.enrichContactFromDocument(
        suggestion.matched_contact_id!,
        {
          document_id: documentId,
          accepted_fields: accepted,
          field_values: fieldValues,
          suggestion_id: suggestion.id,
          confirm_iban: Boolean(suggestion.new_fields?.iban_conflict),
        },
        token,
        orgId,
      )
      onMessage('Fiche contact enrichie.')
    })
  }

  return (
    <section className="panel contact-suggestion-card">
      <h3>{title}</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Confiance {Math.round(suggestion.confidence)} % · confirmation requise
      </p>

      {!editing && (
        <>
          <p style={{ margin: '0.4rem 0 0.2rem', fontWeight: 600 }}>{company}</p>
          <p className="muted" style={{ margin: 0 }}>
            SIRET : {formatSiret(form.siret || suggestion.extracted_data.siret)}
            {(form.city || suggestion.extracted_data.city) &&
              ` · Ville : ${form.city || suggestion.extracted_data.city}`}
          </p>
        </>
      )}

      {suggestion.suggested_action === 'link_existing_contact' && topDup && (
        <p style={{ marginTop: '0.75rem' }}>
          Ce document semble appartenir à : <strong>{topDup.company_name}</strong>
        </p>
      )}

      {suggestion.suggested_action === 'review_possible_duplicate' && topDup && (
        <div style={{ marginTop: '0.75rem' }}>
          <p style={{ margin: 0 }}>
            Contact détecté : <strong>{company}</strong>
          </p>
          <p style={{ margin: '0.35rem 0 0' }}>
            Contact existant : <strong>{topDup.company_name}</strong>
            <span className="muted">
              {' '}
              ({topDup.match_type}, score {topDup.match_score})
            </span>
          </p>
        </div>
      )}

      {suggestion.suggested_action === 'enrich_existing_contact' && (
        <ul style={{ margin: '0.75rem 0 0', paddingLeft: '1.1rem' }}>
          {Object.entries(suggestion.new_fields || {}).map(([key, value]) => (
            <li key={key}>
              {key === 'iban_conflict' ? (
                <span style={{ color: 'var(--danger)' }}>
                  Nouvel IBAN détecté : {String(value)} — vérifiez avant mise à jour.
                </span>
              ) : (
                <>
                  {key} : {String(value)}
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {editing && (
        <form onSubmit={onCreate} className="form-grid" style={{ marginTop: '0.85rem' }}>
          {(
            [
              ['company_name', 'Raison sociale'],
              ['siret', 'SIRET'],
              ['vat_number', 'TVA'],
              ['email', 'E-mail'],
              ['phone', 'Téléphone'],
              ['address_line_1', 'Adresse'],
              ['postal_code', 'Code postal'],
              ['city', 'Ville'],
              ['country', 'Pays'],
              ['iban', 'IBAN'],
              ['bic', 'BIC'],
            ] as const
          ).map(([key, label]) => (
            <div className="field" key={key}>
              <label>{label}</label>
              <input
                value={(form[key] as string) || ''}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
          <div className="actions" style={{ gridColumn: '1 / -1' }}>
            <button className="btn" type="submit" disabled={busy}>
              Enregistrer
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={busy}
              onClick={() => setEditing(false)}
            >
              Annuler
            </button>
          </div>
        </form>
      )}

      {!editing && (
        <div className="actions" style={{ marginTop: '1rem' }}>
          {suggestion.suggested_action === 'create_contact' && (
            <>
              <button className="btn" type="button" disabled={busy} onClick={() => onCreate()}>
                Enregistrer le {roleLabel(suggestion.role, suggestion.suggested_contact_type)}
              </button>
              <button
                className="btn secondary"
                type="button"
                disabled={busy}
                onClick={() => setEditing(true)}
              >
                Modifier les informations
              </button>
            </>
          )}

          {suggestion.suggested_action === 'link_existing_contact' && (
            <button
              className="btn"
              type="button"
              disabled={busy}
              onClick={() => onLink()}
            >
              Associer le document
            </button>
          )}

          {suggestion.suggested_action === 'review_possible_duplicate' && (
            <>
              <button
                className="btn"
                type="button"
                disabled={busy}
                onClick={() => onLink(topDup?.contact_id)}
              >
                Utiliser le contact existant
              </button>
              <button className="btn secondary" type="button" disabled={busy} onClick={() => onCreate()}>
                Créer un nouveau contact
              </button>
              <button
                className="btn secondary"
                type="button"
                disabled={busy}
                onClick={() => setEditing(true)}
              >
                Comparer / modifier
              </button>
            </>
          )}

          {suggestion.suggested_action === 'enrich_existing_contact' && (
            <>
              <button className="btn" type="button" disabled={busy} onClick={onEnrich}>
                Ajouter à la fiche
              </button>
              <button
                className="btn secondary"
                type="button"
                disabled={busy}
                onClick={() => setEditing(true)}
              >
                Modifier
              </button>
            </>
          )}

          <button className="btn secondary" type="button" disabled={busy} onClick={onIgnore}>
            Ignorer
          </button>
        </div>
      )}
    </section>
  )
}
