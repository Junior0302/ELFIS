import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

type Suggestion = {
  title: string
  resource_type: string
  resource_id: string
  action_url?: string | null
}

export default function GlobalSearchBar({ compact = false }: { compact?: boolean }) {
  const { token, orgId } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [open, setOpen] = useState(false)
  const timer = useRef<number | null>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current)
    if (!token || q.trim().length < 2) {
      setSuggestions([])
      return
    }
    timer.current = window.setTimeout(() => {
      api
        .searchSuggestions(q.trim(), 8, token, orgId)
        .then((res) => {
          setSuggestions(res.suggestions)
          setOpen(true)
        })
        .catch(() => setSuggestions([]))
    }, 280)
    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [q, token, orgId])

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    const query = q.trim()
    if (!query) return
    setOpen(false)
    navigate(`/search?q=${encodeURIComponent(query)}`)
  }

  return (
    <div className={`global-search ${compact ? 'compact' : ''}`} ref={wrapRef}>
      <form onSubmit={submit} className="global-search-form" role="search">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Rechercher…"
          aria-label="Recherche ELFIS"
          autoComplete="off"
        />
        <button type="submit" className="btn ghost">
          OK
        </button>
      </form>
      {open && suggestions.length > 0 ? (
        <ul className="global-search-suggestions">
          {suggestions.map((s) => (
            <li key={`${s.resource_type}:${s.resource_id}`}>
              <Link
                to={s.action_url || `/search?q=${encodeURIComponent(s.title)}`}
                onClick={() => setOpen(false)}
              >
                <strong>{s.title}</strong>
                <span className="muted">{s.resource_type}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
