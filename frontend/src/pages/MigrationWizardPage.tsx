import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../auth'
import MigrationIntakePanel from '../components/MigrationIntakePanel'
import MigrationAnalysisPanel from '../components/MigrationAnalysisPanel'
import MigrationExtractionPanel from '../components/MigrationExtractionPanel'
import MigrationValidationPanel from '../components/MigrationValidationPanel'
import MigrationImportPanel from '../components/MigrationImportPanel'
import MigrationDashboard from '../components/MigrationDashboard'
import {
  MIGRATION_SESSION_LS_KEY,
  STEP_LABELS,
  buildCompanySummary,
  isSourceSelectable,
  migrationApi,
  progressPercent,
  sourceAvailabilityBadge,
  validateProfileClient,
  type CompanyProfile,
  type MigrationActivity,
  type MigrationMode,
  type MigrationProgress,
  type MigrationSession,
  type MigrationTimelineEntry,
  type SourceCatalogItem,
} from '../services/migrationApi'

const WIZARD_STEPS = [
  'Bienvenue',
  'Entreprise',
  'Sources',
  'Analyse',
  'Extraction',
  'Validation',
  'Migration',
  'Terminé',
] as const

const AGE_OPTIONS = [
  { value: 'starting_today', label: 'Je démarre aujourd’hui' },
  { value: 'less_than_6_months', label: 'Moins de 6 mois' },
  { value: 'between_6_months_and_2_years', label: 'Entre 6 mois et 2 ans' },
  { value: 'more_than_2_years', label: 'Plus de 2 ans' },
]

const LEGAL_OPTIONS = [
  { value: 'micro_enterprise', label: 'Micro-entreprise' },
  { value: 'sole_proprietorship', label: 'Entreprise individuelle' },
  { value: 'eurl', label: 'EURL' },
  { value: 'sarl', label: 'SARL' },
  { value: 'sasu', label: 'SASU' },
  { value: 'sas', label: 'SAS' },
  { value: 'association', label: 'Association' },
  { value: 'other', label: 'Autre' },
]

const TEAM_OPTIONS = [
  { value: 'one', label: '1 personne' },
  { value: 'two_to_five', label: '2 à 5' },
  { value: 'six_to_twenty', label: '6 à 20' },
  { value: 'more_than_twenty', label: 'Plus de 20' },
]

const ACCOUNTANT_OPTIONS = [
  { value: 'has_accountant', label: 'J’ai un expert-comptable' },
  { value: 'no_accountant', label: 'Pas d’expert-comptable' },
  { value: 'looking_for_accountant', label: 'Je cherche un cabinet' },
]

const JOIN_OPTIONS = [
  { value: 'creating_business', label: 'Je crée mon entreprise' },
  { value: 'changing_software', label: 'Je change de logiciel' },
  { value: 'saving_time', label: 'Gagner du temps' },
  { value: 'current_software_too_expensive', label: 'Logiciel actuel trop cher' },
  { value: 'using_ai', label: 'Utiliser l’IA' },
  { value: 'other', label: 'Autre' },
]

const CATEGORY_LABEL: Record<string, string> = {
  files: 'Fichiers',
  exports: 'Dossiers et exports',
  cloud: 'Cloud',
  other: 'Autre',
}

function emptyProfile(): CompanyProfile {
  return {
    company_age_range: '',
    legal_form: '',
    team_size: '',
    accountant_status: '',
    join_reasons: [],
    other_legal_form: '',
    other_join_reason: '',
  }
}

export default function MigrationWizardPage() {
  const { sessionId: routeSessionId } = useParams()
  const isNew = !routeSessionId || routeSessionId === 'new'
  const { token, orgId } = useAuth()
  const navigate = useNavigate()

  const [session, setSession] = useState<MigrationSession | null>(null)
  const [step, setStep] = useState(1)
  const [mode, setMode] = useState<MigrationMode>('initial_migration')
  const [profile, setProfile] = useState<CompanyProfile>(emptyProfile())
  const [sources, setSources] = useState<string[]>([])
  const [catalog, setCatalog] = useState<SourceCatalogItem[]>([])
  const [timeline, setTimeline] = useState<MigrationTimelineEntry[]>([])
  const [activities, setActivities] = useState<MigrationActivity[]>([])
  const [progress, setProgress] = useState<MigrationProgress | null>(null)
  const [error, setError] = useState('')
  const [saveHint, setSaveHint] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const creatingRef = useRef(false)
  const saveTimer = useRef<number | null>(null)

  const activeStep = Math.min(Math.max(step, 1), 8)

  const persistLocal = (id: string) => {
    try {
      localStorage.setItem(MIGRATION_SESSION_LS_KEY, id)
    } catch {
      /* ignore */
    }
  }

  const loadCatalog = useCallback(async () => {
    if (!token || orgId == null) return
    const data = await migrationApi.sourceCatalog(token, orgId)
    setCatalog(data.items)
  }, [token, orgId])

  const loadSessionExtras = useCallback(
    async (sessionId: string) => {
      if (!token || orgId == null) return
      try {
        const [tl, acts, prog] = await Promise.all([
          migrationApi.getTimeline(token, orgId, sessionId),
          migrationApi.getActivities(token, orgId, sessionId),
          migrationApi.getProgress(token, orgId, sessionId),
        ])
        setTimeline(tl.items)
        setActivities(acts.items.slice(0, 5))
        setProgress(prog.progress)
      } catch {
        /* extras non bloquants */
      }
    },
    [token, orgId],
  )

  const hydrateFromSession = (s: MigrationSession) => {
    setSession(s)
    setMode((s.mode as MigrationMode) || 'initial_migration')
    if (s.company_profile) setProfile({ ...emptyProfile(), ...s.company_profile })
    if (s.selected_sources) setSources([...s.selected_sources])
    const st = s.status
    if (st === 'awaiting_upload' || st === 'sources_selected') setStep(3)
    else if (st === 'profile_completed') setStep(2)
    else setStep(Math.min(s.current_step || 1, 6))
    persistLocal(s.id)
    void loadSessionExtras(s.id)
  }

  useEffect(() => {
    let cancelled = false
    async function boot() {
      if (!token || orgId == null) return
      setLoading(true)
      setError('')
      try {
        await loadCatalog()
        if (isNew) {
          // Pas de création automatique — évite les doublons ; session créée au clic « Commencer »
          setStep(1)
          setLoading(false)
          return
        }
        if (routeSessionId) {
          const s = await migrationApi.getSession(token, orgId, routeSessionId)
          if (!cancelled) hydrateFromSession(s)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Chargement impossible')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [token, orgId, routeSessionId, isNew, loadCatalog])

  const scheduleSaveProfile = (next: CompanyProfile, sess: MigrationSession) => {
    if (!token || orgId == null) return
    if (saveTimer.current) window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => {
      void (async () => {
        const err = validateProfileClient(next)
        if (err) return
        try {
          const updated = await migrationApi.patchProfile(token, orgId, sess.id, next, sess.version)
          setSession(updated)
          setSaveHint('Enregistré')
          void loadSessionExtras(updated.id)
          window.setTimeout(() => setSaveHint(''), 1500)
        } catch (e) {
          setError(e instanceof Error ? e.message : 'Sauvegarde profil échouée')
        }
      })()
    }, 600)
  }

  const scheduleSaveSources = (next: string[], sess: MigrationSession) => {
    if (!token || orgId == null) return
    if (saveTimer.current) window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => {
      void (async () => {
        if (!next.length) return
        try {
          const updated = await migrationApi.patchSources(token, orgId, sess.id, next, sess.version)
          setSession(updated)
          setSaveHint('Enregistré')
          void loadSessionExtras(updated.id)
          window.setTimeout(() => setSaveHint(''), 1500)
        } catch (e) {
          setError(e instanceof Error ? e.message : 'Sauvegarde sources échouée')
        }
      })()
    }, 600)
  }

  async function goWelcomeNext() {
    if (!token || orgId == null) return
    setBusy(true)
    setError('')
    try {
      if (!session) {
        if (creatingRef.current) return
        creatingRef.current = true
        try {
          const created = await migrationApi.createSession(token, orgId, mode)
          hydrateFromSession(created)
          navigate(`/migration/${created.id}`, { replace: true })
          setStep(2)
        } catch (e) {
          const err = e as Error & { code?: string }
          if (err.code === 'initial_migration_active' && mode === 'initial_migration') {
            const list = await migrationApi.listSessions(token, orgId)
            const active = list.items.find(
              (i) =>
                i.mode === 'initial_migration' &&
                !['cancelled', 'completed', 'failed'].includes(i.status),
            )
            if (active) {
              navigate(`/migration/${active.id}`, { replace: true })
              return
            }
          }
          throw e
        } finally {
          creatingRef.current = false
        }
      } else {
        setStep(2)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Création impossible')
    } finally {
      setBusy(false)
    }
  }

  async function goProfileNext() {
    if (!session || !token || orgId == null) return
    const err = validateProfileClient(profile)
    if (err) {
      setError(err)
      return
    }
    setBusy(true)
    setError('')
    try {
      let s = await migrationApi.patchProfile(token, orgId, session.id, profile, session.version)
      if (s.status === 'draft') {
        s = await migrationApi.continueSession(token, orgId, s.id, s.version)
      }
      setSession(s)
      setStep(3)
      void loadSessionExtras(s.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation profil impossible')
    } finally {
      setBusy(false)
    }
  }

  async function goSourcesNext() {
    if (!session || !token || orgId == null) return
    if (!sources.length) {
      setError('Sélectionnez au moins une source.')
      return
    }
    setBusy(true)
    setError('')
    try {
      let s = await migrationApi.patchSources(token, orgId, session.id, sources, session.version)
      if (s.status === 'profile_completed') {
        s = await migrationApi.continueSession(token, orgId, s.id, s.version)
      }
      if (s.status === 'sources_selected') {
        s = await migrationApi.continueSession(token, orgId, s.id, s.version)
      }
      setSession(s)
      setStep(3)
      void loadSessionExtras(s.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation sources impossible')
    } finally {
      setBusy(false)
    }
  }

  function toggleReason(value: string) {
    setProfile((p) => {
      const has = p.join_reasons.includes(value)
      const join_reasons = has ? p.join_reasons.filter((x) => x !== value) : [...p.join_reasons, value]
      const next = { ...p, join_reasons }
      if (session) scheduleSaveProfile(next, session)
      return next
    })
  }

  function toggleSource(id: string, availability: string) {
    if (!isSourceSelectable(availability)) return
    setSources((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
      if (session) scheduleSaveSources(next, session)
      return next
    })
  }

  const byCategory = catalog.reduce<Record<string, SourceCatalogItem[]>>((acc, item) => {
    acc[item.category] = acc[item.category] || []
    acc[item.category].push(item)
    return acc
  }, {})

  const readyMessage =
    session?.status === 'awaiting_upload'
      ? 'Votre espace de migration est prêt. L’étape suivante permettra de déposer et d’analyser vos données.'
      : null

  const pct = progress?.overall_percent ?? progressPercent(session)

  if (loading) return <div className="loading">Préparation de l’assistant…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Assistant de Migration</h2>
          <p>
            <Link to="/migration">← Retour à la liste</Link>
            {saveHint ? <span className="muted migration-save-hint"> · {saveHint}</span> : null}
          </p>
        </div>
      </div>

      {session ? (
        <div className="migration-session-meta panel">
          {pct != null ? (
            <div className="migration-progress-inline" aria-label={`Progression ${pct} %`}>
              <div className="migration-progress-bar">
                <span style={{ width: `${pct}%` }} />
              </div>
              <span className="muted">{pct} % — progression serveur</span>
            </div>
          ) : null}
          {timeline.length > 0 ? (
            <ul className="migration-mini-timeline">
              {timeline.map((t) => (
                <li key={t.id} className={`is-${t.status}`}>
                  {STEP_LABELS[t.step_key] || t.step_key}
                  <span className="muted"> · {t.status}</span>
                </li>
              ))}
            </ul>
          ) : null}
          {activities.length > 0 ? (
            <ul className="migration-activity-feed">
              {activities.map((a) => (
                <li key={a.id}>
                  <strong>{a.title}</strong>
                  {a.occurred_at ? (
                    <span className="muted">
                      {' '}
                      · {new Date(a.occurred_at).toLocaleString('fr-FR')}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
          {session.selected_sources?.length ? (
            <p className="muted">
              Sources : {session.selected_sources.join(', ')}
            </p>
          ) : null}
        </div>
      ) : null}

      <ol className="pipeline-steps migration-wizard-steps">
        {WIZARD_STEPS.map((label, idx) => {
          const n = idx + 1
          const active = n === activeStep
          const done = n < activeStep && n <= 8
          const locked = n > 4
          return (
            <li
              key={label}
              className={[active ? 'is-active' : '', done ? 'is-done' : '', locked ? 'is-locked' : '']
                .filter(Boolean)
                .join(' ')}
              role={n <= 4 && session ? 'button' : undefined}
              tabIndex={n <= 4 && session ? 0 : undefined}
              onClick={() => {
                if (n <= 6 && session) setStep(n)
              }}
            >
              <span>{n}. {label}</span>
            </li>
          )
        })}
      </ol>

      {error ? <div className="panel form-error">{error}</div> : null}

      {activeStep === 1 ? (
        <div className="panel migration-welcome">
          <h3>Bienvenue dans l’Assistant de Migration</h3>
          <p>
            Nous allons préparer votre entreprise sur ComptaPilot. Vous pourrez interrompre la migration à
            tout moment et la reprendre plus tard. Aucune donnée ne sera importée sans votre validation.
          </p>
          <ul className="migration-welcome-list">
            <li>Comprendre votre entreprise</li>
            <li>Analyser vos données</li>
            <li>Détecter automatiquement les informations</li>
            <li>Vous proposer une configuration adaptée</li>
            <li>Importer uniquement ce que vous souhaitez</li>
          </ul>
          <div className="migration-mode-block">
            <p className="muted">Mode de cette session</p>
            <label className="migration-radio">
              <input
                type="radio"
                checked={mode === 'initial_migration'}
                disabled={!!session && !isNew}
                onChange={() => setMode('initial_migration')}
              />
              Migration initiale — importer l’historique de l’entreprise
            </label>
            <label className="migration-radio">
              <input
                type="radio"
                checked={mode === 'one_time_import'}
                disabled={!!session && !isNew}
                onChange={() => setMode('one_time_import')}
              />
              Import ponctuel — ajouter des données à une entreprise déjà configurée
            </label>
          </div>
          <button type="button" className="btn" disabled={busy} onClick={() => void goWelcomeNext()}>
            Commencer
          </button>
        </div>
      ) : null}

      {activeStep === 2 ? (
        <div className="panel migration-profile">
          <h3>Votre entreprise</h3>
          <fieldset>
            <legend>Ancienneté</legend>
            <p className="muted why-hint">Pourquoi cette question ? Pour adapter le niveau d’historique attendu.</p>
            {AGE_OPTIONS.map((o) => (
              <label key={o.value} className="migration-radio">
                <input
                  type="radio"
                  checked={profile.company_age_range === o.value}
                  onChange={() => {
                    const next = { ...profile, company_age_range: o.value }
                    setProfile(next)
                    if (session) scheduleSaveProfile(next, session)
                  }}
                />
                {o.label}
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Statut juridique</legend>
            <p className="muted why-hint">Pourquoi cette question ? Pour préparer les libellés et obligations adaptées.</p>
            {LEGAL_OPTIONS.map((o) => (
              <label key={o.value} className="migration-radio">
                <input
                  type="radio"
                  checked={profile.legal_form === o.value}
                  onChange={() => {
                    const next = { ...profile, legal_form: o.value }
                    setProfile(next)
                    if (session) scheduleSaveProfile(next, session)
                  }}
                />
                {o.label}
              </label>
            ))}
            {profile.legal_form === 'other' ? (
              <input
                className="input"
                placeholder="Précisez la forme"
                value={profile.other_legal_form || ''}
                onChange={(e) => {
                  const next = { ...profile, other_legal_form: e.target.value }
                  setProfile(next)
                  if (session) scheduleSaveProfile(next, session)
                }}
              />
            ) : null}
          </fieldset>
          <fieldset>
            <legend>Taille de l’équipe</legend>
            {TEAM_OPTIONS.map((o) => (
              <label key={o.value} className="migration-radio">
                <input
                  type="radio"
                  checked={profile.team_size === o.value}
                  onChange={() => {
                    const next = { ...profile, team_size: o.value }
                    setProfile(next)
                    if (session) scheduleSaveProfile(next, session)
                  }}
                />
                {o.label}
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Expert-comptable</legend>
            {ACCOUNTANT_OPTIONS.map((o) => (
              <label key={o.value} className="migration-radio">
                <input
                  type="radio"
                  checked={profile.accountant_status === o.value}
                  onChange={() => {
                    const next = { ...profile, accountant_status: o.value }
                    setProfile(next)
                    if (session) scheduleSaveProfile(next, session)
                  }}
                />
                {o.label}
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Pourquoi rejoindre ComptaPilot ?</legend>
            {JOIN_OPTIONS.map((o) => (
              <label key={o.value} className="migration-radio">
                <input
                  type="checkbox"
                  checked={profile.join_reasons.includes(o.value)}
                  onChange={() => toggleReason(o.value)}
                />
                {o.label}
              </label>
            ))}
            {profile.join_reasons.includes('other') ? (
              <input
                className="input"
                placeholder="Précisez"
                value={profile.other_join_reason || ''}
                onChange={(e) => {
                  const next = { ...profile, other_join_reason: e.target.value }
                  setProfile(next)
                  if (session) scheduleSaveProfile(next, session)
                }}
              />
            ) : null}
          </fieldset>
          {validateProfileClient(profile) == null ? (
            <p className="migration-summary">{buildCompanySummary(profile)}</p>
          ) : null}
          <button type="button" className="btn" disabled={busy} onClick={() => void goProfileNext()}>
            Continuer
          </button>
        </div>
      ) : null}

      {activeStep === 3 ? (
        <div className="panel migration-sources">
          <h3>Sources de données</h3>
          <p className="muted">Sélection multiple. Les connecteurs cloud seront branchés dans un prochain sprint.</p>
          {Object.entries(byCategory).map(([cat, items]) => (
            <div key={cat} className="migration-source-group">
              <h4>{CATEGORY_LABEL[cat] || cat}</h4>
              <div className="module-grid migration-source-grid">
                {items.map((item) => {
                  const selectable = isSourceSelectable(item.availability)
                  const badge = sourceAvailabilityBadge(item.availability)
                  const selected = sources.includes(item.id)
                  return (
                    <button
                      key={item.id}
                      type="button"
                      disabled={!selectable}
                      className={`module-card migration-source-card ${selected ? 'is-selected' : ''} ${!selectable ? 'is-disabled' : ''}`}
                      onClick={() => toggleSource(item.id, item.availability)}
                    >
                      <h3>{item.label}</h3>
                      <p>{item.description}</p>
                      {badge ? <span className="badge">{badge}</span> : null}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
          {readyMessage ? <p className="migration-summary">{readyMessage}</p> : null}
          {session?.status === 'awaiting_upload' && token && orgId != null ? (
            <>
              <MigrationIntakePanel
                token={token}
                orgId={orgId}
                migrationSessionId={session.id}
              />
              <button
                type="button"
                className="btn"
                style={{ marginTop: '1rem' }}
                onClick={() => setStep(4)}
              >
                Passer à l’analyse
              </button>
            </>
          ) : null}
          {session?.status !== 'awaiting_upload' ? (
            <button type="button" className="btn" disabled={busy} onClick={() => void goSourcesNext()}>
              Valider les sources
            </button>
          ) : (
            <Link className="btn secondary" to="/migration">
              Retour à la liste
            </Link>
          )}
        </div>
      ) : null}

      {activeStep === 4 && session && token && orgId != null ? (
        <>
          <MigrationAnalysisPanel
            token={token}
            orgId={orgId}
            migrationSessionId={session.id}
          />
          <button
            type="button"
            className="btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setStep(5)}
          >
            Passer à l’extraction
          </button>
        </>
      ) : null}

      {activeStep === 5 && session && token && orgId != null ? (
        <>
          <MigrationExtractionPanel
            token={token}
            orgId={orgId}
            migrationSessionId={session.id}
          />
          <button
            type="button"
            className="btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setStep(6)}
          >
            Passer à la validation
          </button>
        </>
      ) : null}

      {activeStep === 6 && session && token && orgId != null ? (
        <>
          <MigrationValidationPanel
            token={token}
            orgId={orgId}
            migrationSessionId={session.id}
          />
          <button
            type="button"
            className="btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setStep(7)}
          >
            Passer à l&apos;import
          </button>
        </>
      ) : null}

      {activeStep === 7 && session && token && orgId != null ? (
        <>
          <MigrationImportPanel
            token={token}
            orgId={orgId}
            migrationSessionId={session.id}
          />
          <button
            type="button"
            className="btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setStep(8)}
          >
            Passer au tableau de bord
          </button>
        </>
      ) : null}

      {activeStep === 8 && session && token && orgId != null ? (
        <MigrationDashboard
          token={token}
          orgId={orgId}
          migrationSessionId={session.id}
        />
      ) : null}
    </>
  )
}
