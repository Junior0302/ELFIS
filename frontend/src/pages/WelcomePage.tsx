import { useAuth } from '../auth'
import TrialActivationState from '../components/TrialActivationState'
import { resolveCommercialStatus } from '../subscription'
import { useSubscription } from '../subscriptionContext'

/**
 * Welcome Experience — `/welcome` sous PublicLayout (ProductAccessLayout).
 */
export default function WelcomePage() {
  const { user, memberships, orgId } = useAuth()
  const { subscription, loading } = useSubscription()
  const activeMembership = memberships.find((item) => item.organization_id === orgId)
  const canManage = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )

  if (loading) {
    return <div className="loading">Chargement…</div>
  }

  return (
    <TrialActivationState
      commercialStatus={resolveCommercialStatus(subscription)}
      canManage={canManage}
      orgName={activeMembership?.organization_name}
      firstName={user?.first_name?.trim() || ''}
    />
  )
}
