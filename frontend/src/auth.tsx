import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, type Membership, type AuthUser } from './api'
import {
  firebaseLogin,
  firebaseLogout,
  firebaseRegister,
  isFirebaseConfigured,
  mapFirebaseError,
  syncFirestoreMemberships,
} from './firebase'

type AuthState = {
  token: string | null
  user: AuthUser | null
  memberships: Membership[]
  orgId: number | null
  loading: boolean
  firebaseReady: boolean
  login: (email: string, password: string) => Promise<void>
  register: (payload: {
    first_name: string
    last_name: string
    email: string
    password: string
    organization_name?: string
  }) => Promise<void>
  logout: () => void
  setOrgId: (id: number) => void
  setUser: (user: AuthUser) => void
  setMemberships: (memberships: Membership[]) => void
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

const TOKEN_KEY = 'cp_token'
const ORG_KEY = 'cp_org'

function applySession(
  res: { access_token: string; user: AuthUser; memberships: Membership[] },
  setters: {
    setToken: (t: string) => void
    setUser: (u: AuthUser) => void
    setMemberships: (m: Membership[]) => void
    setOrgIdState: (id: number | null) => void
  },
  preferredOrgId?: number | null,
) {
  localStorage.setItem(TOKEN_KEY, res.access_token)
  setters.setToken(res.access_token)
  setters.setUser(res.user)
  setters.setMemberships(res.memberships)
  const preferred =
    preferredOrgId && res.memberships.some((m) => m.organization_id === preferredOrgId)
      ? preferredOrgId
      : null
  const firstOrg = preferred ?? res.memberships[0]?.organization_id ?? null
  setters.setOrgIdState(firstOrg)
  if (firstOrg) localStorage.setItem(ORG_KEY, String(firstOrg))
  else localStorage.removeItem(ORG_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<AuthUser | null>(null)
  const [memberships, setMemberships] = useState<Membership[]>([])
  const [orgId, setOrgIdState] = useState<number | null>(() => {
    const raw = localStorage.getItem(ORG_KEY)
    return raw ? Number(raw) : null
  })
  const [loading, setLoading] = useState(Boolean(token))
  const firebaseReady = isFirebaseConfigured()

  const refreshSession = async () => {
    if (!token) return
    const data = await api.me(token, orgId)
    setUser(data.user)
    setMemberships(data.memberships)
    if (!orgId && data.current_organization_id) {
      setOrgIdState(data.current_organization_id)
      localStorage.setItem(ORG_KEY, String(data.current_organization_id))
    }
  }

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    api
      .me(token, orgId)
      .then((data) => {
        setUser(data.user)
        setMemberships(data.memberships)
        if (!orgId && data.current_organization_id) {
          setOrgIdState(data.current_organization_id)
          localStorage.setItem(ORG_KEY, String(data.current_organization_id))
        }
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
        setMemberships([])
      })
      .finally(() => setLoading(false))
  }, [token, orgId])

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      memberships,
      orgId,
      loading,
      firebaseReady,
      login: async (email, password) => {
        if (!firebaseReady) {
          throw new Error('Connexion indisponible pour le moment. Réessayez plus tard.')
        }
        try {
          const fbUser = await firebaseLogin(email, password)
          const idToken = await fbUser.getIdToken()
          const res = await api.firebaseSession({ id_token: idToken })
          applySession(res, { setToken, setUser, setMemberships, setOrgIdState })
          void syncFirestoreMemberships(res.user, res.memberships).catch((error) => {
            console.error('Synchronisation Firestore impossible', error)
          })
        } catch (err) {
          throw new Error(mapFirebaseError(err))
        }
      },
      register: async (payload) => {
        if (!firebaseReady) {
          throw new Error('Inscription indisponible pour le moment. Réessayez plus tard.')
        }
        try {
          const display = `${payload.first_name} ${payload.last_name}`.trim()
          const fbUser = await firebaseRegister(payload.email, payload.password, display)
          const idToken = await fbUser.getIdToken()
          const res = await api.firebaseSession({
            id_token: idToken,
            first_name: payload.first_name,
            last_name: payload.last_name,
            organization_name: payload.organization_name,
          })
          applySession(res, { setToken, setUser, setMemberships, setOrgIdState })
          void syncFirestoreMemberships(res.user, res.memberships).catch((error) => {
            console.error('Synchronisation Firestore impossible', error)
          })
        } catch (err) {
          throw new Error(mapFirebaseError(err))
        }
      },
      logout: () => {
        void firebaseLogout()
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(ORG_KEY)
        setToken(null)
        setUser(null)
        setMemberships([])
        setOrgIdState(null)
      },
      setOrgId: (id: number) => {
        setOrgIdState(id)
        localStorage.setItem(ORG_KEY, String(id))
        if (token) {
          void api
            .setActiveOrganization(id, token, id)
            .then((res) => {
              localStorage.setItem(TOKEN_KEY, res.access_token)
              setToken(res.access_token)
              setMemberships(res.memberships)
            })
            .catch(() => undefined)
        }
      },
      setUser: (next) => setUser(next),
      setMemberships,
      refreshSession,
    }),
    [token, user, memberships, orgId, loading, firebaseReady],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth hors AuthProvider')
  return ctx
}
