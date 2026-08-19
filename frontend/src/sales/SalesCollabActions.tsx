/**
 * Followers + Assign / Review / Transfer actions (S1.9).
 */
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Badge, Button, FormField, Input, Section, Stack } from '../design-system'
import { Drawer } from '../design-system/overlays'
import type { MentionCandidate, SalesFollower, SalesReview } from './salesCollab'

type Props = {
  entityType: string
  entityId: number
  assignResource?: 'lead' | 'opportunity' | 'task' | 'proposal' | 'activity'
  allowReview?: boolean
  onChanged?: () => void
}

export function SalesCollabActions({
  entityType,
  entityId,
  assignResource,
  allowReview = true,
  onChanged,
}: Props) {
  const { token, orgId, user } = useAuth()
  const [followers, setFollowers] = useState<SalesFollower[]>([])
  const [following, setFollowing] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [transferOpen, setTransferOpen] = useState(false)
  const [candidates, setCandidates] = useState<MentionCandidate[]>([])
  const [ownerId, setOwnerId] = useState('')
  const [reviewerId, setReviewerId] = useState('')
  const [transferTo, setTransferTo] = useState('')
  const [reason, setReason] = useState('handover')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [reviews, setReviews] = useState<SalesReview[]>([])

  const refresh = useCallback(() => {
    if (!token || orgId == null) return
    void api.listSalesFollowers(token, orgId, entityType, entityId).then((rows) => {
      setFollowers(rows)
      setFollowing(rows.some((f) => f.user_id === user?.id))
    })
    void api.listSalesReviews(token, orgId, { status: 'pending', mine: true }).then(setReviews).catch(() => setReviews([]))
  }, [token, orgId, entityType, entityId, user?.id])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    if (!token || orgId == null) return
    void api.listSalesMentionCandidates(token, orgId, '').then(setCandidates).catch(() => setCandidates([]))
  }, [token, orgId])

  const toggleFollow = async () => {
    if (!token || orgId == null) return
    setBusy(true)
    try {
      if (following) await api.unfollowSalesResource(token, orgId, entityType, entityId)
      else await api.followSalesResource(token, orgId, { entity_type: entityType, entity_id: entityId })
      refresh()
    } finally {
      setBusy(false)
    }
  }

  const runAssign = async () => {
    if (!token || orgId == null || !assignResource || !ownerId) return
    setBusy(true)
    setError('')
    try {
      await api.assignSalesResource(token, orgId, {
        resource: assignResource,
        resource_id: entityId,
        owner_user_id: Number(ownerId),
        comment: comment || undefined,
      })
      setAssignOpen(false)
      onChanged?.()
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Assignation impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  const runReview = async () => {
    if (!token || orgId == null || !reviewerId) return
    setBusy(true)
    setError('')
    try {
      const et =
        entityType === 'opportunity' || entityType === 'proposal' || entityType === 'workspace'
          ? entityType
          : 'opportunity'
      await api.createSalesReview(token, orgId, {
        entity_type: et,
        entity_id: entityId,
        reviewer_user_id: Number(reviewerId),
        message: comment || undefined,
      })
      setReviewOpen(false)
      refresh()
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Revue impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  const runTransfer = async () => {
    if (!token || orgId == null || !transferTo || !reason.trim()) return
    setBusy(true)
    setError('')
    try {
      await api.transferSalesOwnership(token, orgId, {
        entity_type: entityType,
        entity_id: entityId,
        to_user_id: Number(transferTo),
        reason: reason.trim(),
        comment: comment || undefined,
      })
      setTransferOpen(false)
      onChanged?.()
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Transfert impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  const decide = async (reviewId: number, decision: string) => {
    if (!token || orgId == null) return
    await api.decideSalesReview(token, orgId, reviewId, { decision })
    refresh()
  }

  return (
    <Section title="Collaboration" spacing="compact">
      <Stack gap={2}>
        <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
          <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => void toggleFollow()}>
            {following ? 'Ne plus suivre' : 'Suivre'}
          </Button>
          {assignResource ? (
            <Button type="button" size="sm" variant="secondary" onClick={() => setAssignOpen(true)}>
              Assigner
            </Button>
          ) : null}
          {allowReview ? (
            <Button type="button" size="sm" variant="secondary" onClick={() => setReviewOpen(true)}>
              Demander une revue
            </Button>
          ) : null}
          <Button type="button" size="sm" variant="secondary" onClick={() => setTransferOpen(true)}>
            Transférer
          </Button>
        </div>

        <p className="muted">
          Abonnés :{' '}
          {followers.length === 0
            ? 'aucun'
            : followers.map((f) => f.user_label || `#${f.user_id}`).join(', ')}
        </p>

        {reviews.filter((r) => r.entity_type === entityType && r.entity_id === entityId).length > 0 ? (
          <ul className="sales-workspace__list">
            {reviews
              .filter((r) => r.entity_type === entityType && r.entity_id === entityId)
              .map((r) => (
                <li key={r.id} className="sales-workspace__list-item">
                  <Badge tone="warn">Revue #{r.id}</Badge>
                  <div className="sales-deal__header-actions">
                    <Button type="button" size="sm" variant="primary" onClick={() => void decide(r.id, 'approved')}>
                      Valider
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => void decide(r.id, 'changes_requested')}
                    >
                      Modifications
                    </Button>
                    <Button type="button" size="sm" variant="danger" onClick={() => void decide(r.id, 'rejected')}>
                      Refuser
                    </Button>
                  </div>
                </li>
              ))}
          </ul>
        ) : null}
      </Stack>

      <Drawer
        open={assignOpen}
        onOpenChange={setAssignOpen}
        title="Assigner"
        description="Le backend applique le propriétaire — pas de logique locale."
        size="md"
        side="right"
        footer={
          <Button type="button" variant="primary" disabled={busy || !ownerId} onClick={() => void runAssign()}>
            Confirmer
          </Button>
        }
      >
        <Stack gap={3}>
          <FormField label="Nouveau propriétaire (user id)" htmlFor="assign-owner">
            <Input id="assign-owner" value={ownerId} onChange={(e) => setOwnerId(e.target.value)} />
          </FormField>
          <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
            {candidates.map((c) => (
              <Button key={c.user_id} type="button" size="sm" variant="secondary" onClick={() => setOwnerId(String(c.user_id))}>
                {c.label}
              </Button>
            ))}
          </div>
          {error ? <p role="alert">{error}</p> : null}
        </Stack>
      </Drawer>

      <Drawer
        open={reviewOpen}
        onOpenChange={setReviewOpen}
        title="Demande de revue"
        size="md"
        side="right"
        footer={
          <Button type="button" variant="primary" disabled={busy || !reviewerId} onClick={() => void runReview()}>
            Envoyer
          </Button>
        }
      >
        <Stack gap={3}>
          <FormField label="Reviewer (user id)" htmlFor="reviewer">
            <Input id="reviewer" value={reviewerId} onChange={(e) => setReviewerId(e.target.value)} />
          </FormField>
          <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
            {candidates.map((c) => (
              <Button
                key={c.user_id}
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setReviewerId(String(c.user_id))}
              >
                {c.label}
              </Button>
            ))}
          </div>
          <FormField label="Message" htmlFor="review-msg">
            <Input id="review-msg" value={comment} onChange={(e) => setComment(e.target.value)} />
          </FormField>
          {error ? <p role="alert">{error}</p> : null}
        </Stack>
      </Drawer>

      <Drawer
        open={transferOpen}
        onOpenChange={setTransferOpen}
        title="Transfert de propriété"
        description="Audit + notification + Event Bus. Confirmation requise."
        size="md"
        side="right"
        footer={
          <Button
            type="button"
            variant="danger"
            disabled={busy || !transferTo || !reason.trim()}
            onClick={() => void runTransfer()}
          >
            Confirmer le transfert
          </Button>
        }
      >
        <Stack gap={2}>
          <FormField label="Nouveau propriétaire" htmlFor="transfer-to">
            <Input id="transfer-to" value={transferTo} onChange={(e) => setTransferTo(e.target.value)} />
          </FormField>
          <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
            {candidates.map((c) => (
              <Button
                key={c.user_id}
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setTransferTo(String(c.user_id))}
              >
                {c.label}
              </Button>
            ))}
          </div>
          <FormField label="Motif" htmlFor="transfer-reason">
            <Input id="transfer-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          </FormField>
          {error ? <p role="alert">{error}</p> : null}
        </Stack>
      </Drawer>
    </Section>
  )
}
