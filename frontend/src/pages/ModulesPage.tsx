import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type ModuleInfo } from '../api'

const STATUS_LABEL: Record<ModuleInfo['status'], string> = {
  live: 'Disponible',
  setup: 'À configurer',
}

export default function ModulesPage() {
  const [modules, setModules] = useState<ModuleInfo[]>([])
  const [vision, setVision] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .listModules()
      .then((data) => {
        setModules(data.modules)
        setVision(data.vision)
      })
      .catch((e) => setError(e.message || 'Impossible de charger les modules'))
  }, [])

  if (error) return <div className="panel form-error">{error}</div>
  if (!modules.length) return <div className="loading">Chargement des fonctionnalités…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Modules</h2>
          <p>
            {vision ||
              'Chaque module sert un besoin du dirigeant — cliquez pour ouvrir celui qui vous intéresse.'}
          </p>
        </div>
      </div>

      <div className="module-grid">
        {modules.map((mod) => {
          const inner = (
            <>
              <div className="module-card-top">
                <span className="module-id">M{mod.id}</span>
                <span className={`badge status-${mod.status}`}>{STATUS_LABEL[mod.status]}</span>
              </div>
              <h3>{mod.name}</h3>
              <p>{mod.summary}</p>
            </>
          )
          return mod.route ? (
            <Link key={mod.slug} to={mod.route} className={`module-card is-${mod.status}`}>
              {inner}
            </Link>
          ) : (
            <div key={mod.slug} className={`module-card is-${mod.status} disabled`}>
              {inner}
            </div>
          )
        })}
      </div>
    </>
  )
}
