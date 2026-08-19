/**
 * Quick Create Drawer — création légère sans quitter le contexte (S1.8).
 */
import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Button, FormField, Input, Stack } from '../design-system'
import { Drawer } from '../design-system/overlays'
import type { QuickCreateKind } from './salesOps'

type Props = {
  open: boolean
  kind: QuickCreateKind | null
  onOpenChange: (open: boolean) => void
  onCreated?: (kind: QuickCreateKind, id: number) => void
  context?: {
    opportunity_id?: number | null
    company_id?: number | null
    entity_type?: string
    entity_id?: number
  }
}

const TITLES: Record<QuickCreateKind, string> = {
  lead: 'Nouveau lead',
  company: 'Nouvelle entreprise',
  person: 'Nouveau contact',
  opportunity: 'Nouvelle opportunité',
  task: 'Nouvelle tâche',
  activity: 'Nouvelle activité',
  note: 'Nouvelle note',
}

export function QuickCreateDrawer({ open, kind, onOpenChange, onCreated, context }: Props) {
  const { token, orgId } = useAuth()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [title, setTitle] = useState('')
  const [name, setName] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [activityType, setActivityType] = useState('call')
  const submitting = useRef(false)
  const firstFieldId = useId()
  const firstRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) {
      setError('')
      setBusy(false)
      submitting.current = false
      return
    }
    // Restore draft if present
    try {
      const raw = localStorage.getItem(`salespilot:qc:${kind}`)
      if (raw) {
        const draft = JSON.parse(raw) as Record<string, string>
        setTitle(draft.title || '')
        setName(draft.name || '')
        setFirstName(draft.firstName || '')
        setLastName(draft.lastName || '')
        setEmail(draft.email || '')
        setSubject(draft.subject || '')
        setBody(draft.body || '')
        if (draft.activityType) setActivityType(draft.activityType)
      } else {
        setTitle('')
        setName('')
        setFirstName('')
        setLastName('')
        setEmail('')
        setSubject('')
        setBody('')
      }
    } catch {
      setTitle('')
      setName('')
      setFirstName('')
      setLastName('')
      setEmail('')
      setSubject('')
      setBody('')
    }
  }, [open, kind])

  useEffect(() => {
    if (!open || !kind) return
    const draft = {
      title,
      name,
      firstName,
      lastName,
      email,
      subject,
      body,
      activityType,
    }
    const t = window.setTimeout(() => {
      localStorage.setItem(`salespilot:qc:${kind}`, JSON.stringify(draft))
    }, 400)
    return () => window.clearTimeout(t)
  }, [open, kind, title, name, firstName, lastName, email, subject, body, activityType])

  const submit = async () => {
    if (!token || orgId == null || !kind || busy || submitting.current) return
    submitting.current = true
    setBusy(true)
    setError('')
    try {
      let id = 0
      if (kind === 'lead') {
        const row = await api.createSalesLead(token, orgId, {
          title: title.trim() || 'Nouveau lead',
          email: email || undefined,
        })
        id = row.id
      } else if (kind === 'company') {
        const row = await api.createSalesCompany(token, orgId, {
          name: name.trim() || 'Nouvelle entreprise',
          email: email || undefined,
        })
        id = row.id
      } else if (kind === 'person') {
        const row = await api.createSalesPerson(token, orgId, {
          first_name: firstName.trim() || 'Prénom',
          last_name: lastName.trim() || 'Nom',
          email: email || undefined,
          company_id: context?.company_id ?? undefined,
        })
        id = row.id
      } else if (kind === 'opportunity') {
        const row = await api.createSalesOpportunity(token, orgId, {
          name: title.trim() || 'Nouvelle opportunité',
          company_id: context?.company_id ?? undefined,
        })
        id = row.id
      } else if (kind === 'task') {
        const row = await api.createSalesTask(token, orgId, {
          title: title.trim() || 'Nouvelle tâche',
          opportunity_id: context?.opportunity_id ?? undefined,
        })
        id = row.id
      } else if (kind === 'activity') {
        const row = await api.createSalesActivity(token, orgId, {
          activity_type: activityType,
          subject: subject.trim() || title.trim() || 'Activité',
          activity_at: new Date().toISOString(),
          opportunity_id: context?.opportunity_id ?? undefined,
        })
        id = row.id
      } else if (kind === 'note') {
        if (!context?.entity_type || !context?.entity_id) {
          throw new Error('Contexte entité requis pour une note')
        }
        const row = await api.createSalesNote(token, orgId, {
          body_markdown: body.trim() || 'Note',
          entity_type: context.entity_type,
          entity_id: context.entity_id,
        })
        id = row.id
      }
      onCreated?.(kind, id)
      try {
        localStorage.removeItem(`salespilot:qc:${kind}`)
      } catch {
        /* ignore */
      }
      onOpenChange(false)
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Création impossible',
      )
    } finally {
      setBusy(false)
      submitting.current = false
    }
  }

  if (!kind) return null

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={TITLES[kind]}
      description="Saisie rapide — validation serveur. Anti double-clic actif."
      size="md"
      side="right"
      initialFocusRef={firstRef}
      footer={
        <div className="sales-deal__header-actions">
          <Button type="button" variant="secondary" disabled={busy} onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button type="button" variant="primary" disabled={busy} onClick={() => void submit()}>
            {busy ? 'Enregistrement…' : 'Créer'}
          </Button>
        </div>
      }
    >
      <Stack gap={3}>
        {error ? (
          <p className="muted" role="alert">
            {error}
          </p>
        ) : null}

        {(kind === 'lead' || kind === 'opportunity' || kind === 'task') && (
          <FormField label="Titre" htmlFor={firstFieldId}>
            <Input
              id={firstFieldId}
              ref={firstRef}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void submit()
              }}
            />
          </FormField>
        )}

        {kind === 'company' && (
          <FormField label="Nom" htmlFor={firstFieldId}>
            <Input
              id={firstFieldId}
              ref={firstRef}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </FormField>
        )}

        {kind === 'person' && (
          <>
            <FormField label="Prénom" htmlFor={firstFieldId}>
              <Input
                id={firstFieldId}
                ref={firstRef}
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </FormField>
            <FormField label="Nom" htmlFor={`${firstFieldId}-last`}>
              <Input
                id={`${firstFieldId}-last`}
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </FormField>
          </>
        )}

        {(kind === 'lead' || kind === 'company' || kind === 'person') && (
          <FormField label="Email" htmlFor={`${firstFieldId}-email`}>
            <Input
              id={`${firstFieldId}-email`}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormField>
        )}

        {kind === 'activity' && (
          <>
            <FormField label="Type" htmlFor={`${firstFieldId}-type`}>
              <select
                id={`${firstFieldId}-type`}
                value={activityType}
                onChange={(e) => setActivityType(e.target.value)}
              >
                <option value="call">Appel</option>
                <option value="email">Email</option>
                <option value="meeting">Réunion</option>
                <option value="visit">Visite</option>
              </select>
            </FormField>
            <FormField label="Sujet" htmlFor={firstFieldId}>
              <Input
                id={firstFieldId}
                ref={firstRef}
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
            </FormField>
          </>
        )}

        {kind === 'note' && (
          <FormField label="Contenu" htmlFor={firstFieldId}>
            <textarea
              id={firstFieldId}
              ref={firstRef as never}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={6}
              style={{ width: '100%' }}
            />
          </FormField>
        )}
      </Stack>
    </Drawer>
  )
}
