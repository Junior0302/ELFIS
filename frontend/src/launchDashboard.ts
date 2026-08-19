/** Types + helpers Launch Dashboard (C1.12). */

export type LaunchStep = {
  key: string
  label: string
  completed: boolean
  action_path?: string | null
  action_label?: string | null
}

export type LaunchRecommendedAction = {
  key: string
  title: string
  description: string
  action_label: string
  action_path: string
}

export type LaunchQuickAction = {
  key: string
  label: string
  description: string
  path: string
  enabled: boolean
}

export type LaunchActivityItem = {
  id: string
  type: string
  title: string
  description: string
  occurred_at: string
  path?: string | null
}

export type LaunchDashboardData = {
  workspace_ready: boolean
  user: { display_name: string | null }
  organization: { name: string }
  onboarding: {
    completed_steps: number
    total_steps: number
    progress: number
    steps: LaunchStep[]
    recommended_action: LaunchRecommendedAction | null
    all_completed: boolean
  }
  quick_actions: LaunchQuickAction[]
  recent_activity: LaunchActivityItem[]
}

export function launchWelcomeTitle(displayName: string | null | undefined): string {
  const name = (displayName || '').trim()
  if (name) return `Bonjour ${name}`
  return 'Bienvenue dans ComptaPilot'
}

export function launchWelcomeLead(orgName: string, workspaceReady: boolean): string {
  const org = (orgName || '').trim() || 'votre organisation'
  if (workspaceReady) return `L’espace de ${org} est prêt.`
  return `Préparez l’espace de ${org} pour démarrer.`
}
