import { useCallback, useEffect, useState } from 'react'
import {
  fieldStatusLabel,
  validationApi,
  validationStatusLabel,
  type DuplicateItem,
  type HistoryEntry,
  type MatchItem,
  type ValidationField,
  type ValidationSession,
} from '../services/validationApi'

type Props = {
  token: string
  orgId: number
  migrationSessionId: string
}

export default function MigrationValidationPanel({ token, orgId, migrationSessionId }: Props) {
  const [items, setItems] = useState<ValidationSession[]>([])
  const [filter, setFilter] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [statusMessage, setStatusMessage] = useState('Validation humaine')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [fields, setFields] = useState<ValidationField[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [duplicates, setDuplicates] = useState<DuplicateItem[]>([])
  const [matches, setMatches] = useState<MatchItem[]>([])
  const [editPath, setEditPath] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const reload = useCallback(async () => {
    const data = await validationApi.listSessions(token, orgId, migrationSessionId)
    setItems(data.items)
  }, [token, orgId, migrationSessionId])

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        await reload()
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Chargement impossible')
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [reload])

  async function startValidation() {
    if (busy) return
    setBusy(true)
    setError('')
    setStatusMessage('Ouverture des sessions…')
    try {
      const res = await validationApi.startSession(token, orgId, migrationSessionId)
      await reload()
      setStatusMessage(`${res.started} document(s) en validation`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Démarrage impossible')
    } finally {
      setBusy(false)
    }
  }

  async function openDetail(id: string) {
    setActiveId(id)
    setEditPath(null)
    try {
      const [f, h, d, m] = await Promise.all([
        validationApi.getFields(token, orgId, id),
        validationApi.history(token, orgId, id),
        validationApi.duplicates(token, orgId, id),
        validationApi.matching(token, orgId, id),
      ])
      setFields(f.fields)
      setHistory(h.items)
      setDuplicates(d.items)
      setMatches(m.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Détail impossible')
    }
  }

  async function acceptField(path: string) {
    if (!activeId || busy) return
    setBusy(true)
    try {
      await validationApi.editField(token, orgId, activeId, path, { action: 'accept' })
      await openDetail(activeId)
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Acceptation impossible')
    } finally {
      setBusy(false)
    }
  }

  async function saveEdit() {
    if (!activeId || !editPath || busy) return
    setBusy(true)
    try {
      let value: unknown = editValue
      try {
        value = JSON.parse(editValue)
      } catch {
        /* string */
      }
      await validationApi.editField(token, orgId, activeId, editPath, {
        action: 'edit',
        value,
        reason: 'correction_humaine',
      })
      setEditPath(null)
      await openDetail(activeId)
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Édition impossible')
    } finally {
      setBusy(false)
    }
  }

  async function validateDoc(id: string) {
    if (busy) return
    setBusy(true)
    try {
      await validationApi.validate(token, orgId, id)
      await reload()
      if (activeId === id) await openDetail(id)
      setStatusMessage('Document prêt pour import (non exécuté)')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation impossible')
    } finally {
      setBusy(false)
    }
  }

  async function rejectDoc(id: string) {
    if (busy) return
    setBusy(true)
    try {
      await validationApi.reject(token, orgId, id, 'rejet_utilisateur')
      await reload()
      setStatusMessage('Document rejeté')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rejet impossible')
    } finally {
      setBusy(false)
    }
  }

  async function resolveMatch(matchId: string, resolution: string) {
    if (busy) return
    setBusy(true)
    try {
      await validationApi.resolveMatch(token, orgId, matchId, resolution)
      if (activeId) await openDetail(activeId)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Résolution impossible')
    } finally {
      setBusy(false)
    }
  }

  const filtered = items.filter((i) => {
    if (!filter.trim()) return true
    const q = filter.toLowerCase()
    return (
      (i.universal_document_id || '').toLowerCase().includes(q) ||
      i.document_id.toLowerCase().includes(q) ||
      i.status.toLowerCase().includes(q)
    )
  })

  const active = items.find((i) => i.id === activeId) || null
  const ready = items.filter((i) => i.status === 'ready_for_import').length

  return (
    <div className="migration-validation panel">
      <h3>Validation & Mapping</h3>
      <p className="muted">
        Correction humaine, doublons et rapprochements. Aucun import métier, aucune création
        automatique de fiche.
      </p>

      <div className="migration-analysis-toolbar">
        <button type="button" className="btn" disabled={busy} onClick={() => void startValidation()}>
          {busy ? 'Traitement…' : 'Ouvrir la validation'}
        </button>
        <button type="button" className="btn secondary" disabled={busy} onClick={() => void reload()}>
          Actualiser
        </button>
        <input
          type="search"
          placeholder="Filtrer…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filtrer les documents"
        />
        <span className="muted">{statusMessage} · Prêts : {ready}</span>
      </div>

      {error ? <div className="form-error">{error}</div> : null}

      <ul className="migration-analysis-list">
        {filtered.map((r) => (
          <li key={r.id} className={`is-${r.status}`}>
            <div className="migration-progress-bar" aria-label="Progression">
              <span style={{ width: `${r.progress_percent}%` }} />
            </div>
            <div>
              <strong>
                {r.universal_document_id || r.document_id.slice(0, 8)} ·{' '}
                {validationStatusLabel(r.status)}
              </strong>
              <p className="muted">
                Erreurs {r.errors?.length || 0} · Warnings {r.warnings?.length || 0} · Doublons{' '}
                {Number((r.duplicate_summary as { count?: number })?.count) || 0}
              </p>
              <div className="migration-analysis-toolbar">
                <button type="button" className="btn secondary" onClick={() => void openDetail(r.id)}>
                  Ouvrir
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={busy || r.status === 'ready_for_import' || r.status === 'rejected'}
                  onClick={() => void validateDoc(r.id)}
                >
                  Valider document
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={busy || r.status === 'rejected'}
                  onClick={() => void rejectDoc(r.id)}
                >
                  Rejeter
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {!items.length ? (
        <p className="muted">
          Aucune session. Passez d’abord l’extraction jusqu’à l’attente de validation humaine.
        </p>
      ) : null}

      {active ? (
        <div className="migration-extraction-detail">
          <h4>Détail — {active.universal_document_id || active.id.slice(0, 8)}</h4>
          <p className="muted">Comparaison IA / utilisateur · historique append-only</p>

          <section>
            <h5>Champs</h5>
            <ul className="migration-analysis-list">
              {fields.map((f) => {
                const low = (f.confidence ?? 1) < 0.7
                return (
                  <li key={f.field_path} className={low ? 'form-error' : undefined}>
                    <strong>
                      {f.field_path} · {fieldStatusLabel(f.status)}
                      {f.confidence != null ? ` · ${Math.round(f.confidence * 100)}%` : ''}
                    </strong>
                    <p className="muted">
                      IA : {JSON.stringify(f.ai_value)} → Actuel : {JSON.stringify(f.current_value)}
                    </p>
                    <p className="muted">
                      Provenance : {String(f.provenance?.source || '—')} /{' '}
                      {String(f.provenance?.extractor_name || '—')}
                    </p>
                    <div className="migration-analysis-toolbar">
                      <button
                        type="button"
                        className="btn secondary"
                        disabled={busy}
                        onClick={() => void acceptField(f.field_path)}
                      >
                        Valider champ
                      </button>
                      <button
                        type="button"
                        className="btn secondary"
                        onClick={() => {
                          setEditPath(f.field_path)
                          setEditValue(
                            typeof f.current_value === 'string'
                              ? f.current_value
                              : JSON.stringify(f.current_value ?? ''),
                          )
                        }}
                      >
                        Modifier
                      </button>
                    </div>
                  </li>
                )
              })}
            </ul>
            {editPath ? (
              <div>
                <p className="muted">Édition : {editPath}</p>
                <input
                  type="text"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  style={{ width: '100%' }}
                />
                <button type="button" className="btn" disabled={busy} onClick={() => void saveEdit()}>
                  Enregistrer
                </button>
                <button type="button" className="btn secondary" onClick={() => setEditPath(null)}>
                  Annuler modification
                </button>
              </div>
            ) : null}
          </section>

          <section>
            <h5>Doublons (propositions)</h5>
            {!duplicates.length ? <p className="muted">Aucun doublon détecté</p> : null}
            <ul>
              {duplicates.map((d) => (
                <li key={d.id} className="muted">
                  {d.severity} · {Math.round(d.score * 100)}% · {d.explanation} ·{' '}
                  {d.other_universal_document_id || d.other_document_id}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h5>Matching (aucune création)</h5>
            <ul>
              {matches.map((m) => (
                <li key={m.id}>
                  <span className="muted">
                    {m.party_role} · {m.category} · {Math.round(m.score * 100)}% ·{' '}
                    {m.contact_label || 'aucun'} · {m.resolution}
                  </span>
                  <div className="migration-analysis-toolbar">
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={busy || !m.contact_id}
                      onClick={() => void resolveMatch(m.id, 'use_existing')}
                    >
                      Associer fiche existante
                    </button>
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={busy}
                      onClick={() => void resolveMatch(m.id, 'create_later')}
                    >
                      Créer plus tard
                    </button>
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={busy}
                      onClick={() => void resolveMatch(m.id, 'ignore')}
                    >
                      Ignorer
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h5>Historique</h5>
            <ul>
              {history.map((h) => (
                <li key={h.id} className="muted">
                  {h.created_at} · {h.action} · {h.field_path} : {JSON.stringify(h.old_value)} →{' '}
                  {JSON.stringify(h.new_value)}
                </li>
              ))}
            </ul>
          </section>

          <p className="muted">Aucun bouton Import dans ce sprint.</p>
          <button type="button" className="btn secondary" onClick={() => setActiveId(null)}>
            Fermer
          </button>
        </div>
      ) : null}
    </div>
  )
}
