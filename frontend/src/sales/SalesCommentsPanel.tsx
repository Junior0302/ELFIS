/**
 * Panneau commentaires collaboratifs — mentions @[id:Label] (S1.9).
 */
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Badge, Button, FormField, Input, Section, Stack } from '../design-system'
import { formatMention, type MentionCandidate, type SalesComment } from './salesCollab'

type Props = {
  entityType: string
  entityId: number
}

export function SalesCommentsPanel({ entityType, entityId }: Props) {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<SalesComment[]>([])
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [candidates, setCandidates] = useState<MentionCandidate[]>([])
  const [mentionQ, setMentionQ] = useState('')

  const refresh = useCallback(() => {
    if (!token || orgId == null) return
    void api
      .listSalesComments(token, orgId, entityType, entityId)
      .then(setItems)
      .catch(() => setItems([]))
  }, [token, orgId, entityType, entityId])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    if (!token || orgId == null || !mentionQ.trim()) {
      setCandidates([])
      return
    }
    const t = window.setTimeout(() => {
      void api.listSalesMentionCandidates(token, orgId, mentionQ).then(setCandidates).catch(() => setCandidates([]))
    }, 250)
    return () => window.clearTimeout(t)
  }, [token, orgId, mentionQ])

  const submit = async () => {
    if (!token || orgId == null || !body.trim() || busy) return
    setBusy(true)
    setError('')
    try {
      await api.createSalesComment(token, orgId, {
        entity_type: entityType,
        entity_id: entityId,
        body: body.trim(),
      })
      setBody('')
      refresh()
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Envoi impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section title="Commentaires" spacing="compact">
      <Stack gap={3}>
        {items.length === 0 ? (
          <p className="muted">Aucun commentaire — discussion métier uniquement.</p>
        ) : (
          <ul className="sales-workspace__list">
            {items.map((c) => (
              <li key={c.id} className="sales-workspace__list-item">
                <header className="sales-workspace__meta-row">
                  <strong>{c.author_label || 'Utilisateur'}</strong>
                  <Badge tone="neutral">
                    {new Date(c.created_at).toLocaleString('fr-FR', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </Badge>
                  {c.edited_at ? <Badge tone="accent">Modifié</Badge> : null}
                </header>
                <p style={{ whiteSpace: 'pre-wrap' }}>{c.body}</p>
                {c.mentions?.length ? (
                  <p className="muted">
                    Mentions : {c.mentions.map((m) => m.label).join(', ')}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        <FormField label="Nouveau commentaire" htmlFor="sales-comment-body">
          <textarea
            id="sales-comment-body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={4}
            style={{ width: '100%' }}
            placeholder="Texte… Mention : @[id:Nom] via la recherche ci-dessous."
          />
        </FormField>

        <FormField label="Mentionner" htmlFor="sales-mention-q">
          <Input
            id="sales-mention-q"
            value={mentionQ}
            onChange={(e) => setMentionQ(e.target.value)}
            placeholder="Rechercher un collègue…"
          />
        </FormField>
        {candidates.length > 0 ? (
          <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
            {candidates.map((c) => (
              <Button
                key={c.user_id}
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  setBody((cur) => `${cur}${cur ? ' ' : ''}${formatMention(c.user_id, c.label)}`)
                  setMentionQ('')
                  setCandidates([])
                }}
              >
                @{c.label}
              </Button>
            ))}
          </div>
        ) : null}

        {error ? (
          <p className="muted" role="alert">
            {error}
          </p>
        ) : null}
        <Button type="button" variant="primary" disabled={busy || !body.trim()} onClick={() => void submit()}>
          {busy ? 'Envoi…' : 'Publier'}
        </Button>
      </Stack>
    </Section>
  )
}
