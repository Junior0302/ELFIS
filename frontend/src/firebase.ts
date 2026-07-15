import { initializeApp, type FirebaseApp } from 'firebase/app'
import {
  createUserWithEmailAndPassword,
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  updatePassword,
  updateProfile,
  type Auth,
  type User as FirebaseUser,
} from 'firebase/auth'
import { doc, getFirestore, serverTimestamp, setDoc, type Firestore } from 'firebase/firestore'
import { getDownloadURL, getStorage, ref, uploadBytes, type FirebaseStorage } from 'firebase/storage'

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string | undefined,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET as string | undefined,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID as string | undefined,
  appId: import.meta.env.VITE_FIREBASE_APP_ID as string | undefined,
}

export function isFirebaseConfigured(): boolean {
  return Boolean(config.apiKey && config.authDomain && config.projectId && config.appId)
}

let app: FirebaseApp | null = null
let auth: Auth | null = null
let firestore: Firestore | null = null
let storage: FirebaseStorage | null = null

export function getFirebaseAuth(): Auth {
  if (!isFirebaseConfigured()) {
    throw new Error(
      'Firebase non configuré. Renseignez VITE_FIREBASE_* dans frontend/.env puis redémarrez Vite.',
    )
  }
  if (!app) {
    app = initializeApp({
      apiKey: config.apiKey!,
      authDomain: config.authDomain!,
      projectId: config.projectId!,
      storageBucket: config.storageBucket || undefined,
      messagingSenderId: config.messagingSenderId || undefined,
      appId: config.appId!,
    })
    auth = getAuth(app)
  }
  return auth!
}

function getFirebaseApp(): FirebaseApp {
  getFirebaseAuth()
  return app!
}

export function getFirebaseFirestore(): Firestore {
  if (!firestore) firestore = getFirestore(getFirebaseApp())
  return firestore
}

function getFirebaseStorage(): FirebaseStorage {
  if (!storage) storage = getStorage(getFirebaseApp())
  return storage
}

function requireFirebaseUser(): FirebaseUser {
  const user = getFirebaseAuth().currentUser
  if (!user) throw new Error('Session Firebase expirée. Reconnectez-vous.')
  return user
}

export async function firebaseLogin(email: string, password: string): Promise<FirebaseUser> {
  const result = await signInWithEmailAndPassword(getFirebaseAuth(), email, password)
  return result.user
}

export async function firebaseRegister(
  email: string,
  password: string,
  displayName: string,
): Promise<FirebaseUser> {
  const result = await createUserWithEmailAndPassword(getFirebaseAuth(), email, password)
  if (displayName.trim()) {
    await updateProfile(result.user, { displayName: displayName.trim() })
  }
  return result.user
}

export async function firebaseLogout(): Promise<void> {
  if (!isFirebaseConfigured() || !auth) return
  await signOut(auth)
}

export async function updateFirebaseUserPassword(password: string): Promise<void> {
  await updatePassword(requireFirebaseUser(), password)
}

export async function saveFirestoreProfile(profile: {
  first_name: string
  last_name: string
  email: string
  phone?: string
  avatar?: string
}): Promise<void> {
  const user = requireFirebaseUser()
  await setDoc(
    doc(getFirebaseFirestore(), 'users', user.uid),
    {
      firstName: profile.first_name,
      lastName: profile.last_name,
      email: profile.email,
      phone: profile.phone || '',
      avatar: profile.avatar || user.photoURL || '',
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  )
}

export async function syncFirestoreMemberships(
  profile: { first_name: string; last_name: string; email: string; phone?: string; avatar?: string },
  memberships: {
    organization_id: number
    organization_name: string
    role: string
    permissions: string[]
    country: string
  }[],
): Promise<void> {
  const user = requireFirebaseUser()
  await saveFirestoreProfile(profile)

  for (const membership of memberships) {
    if (membership.role !== 'owner') continue
    const orgId = String(membership.organization_id)
    await setDoc(
      doc(getFirebaseFirestore(), 'organizations', orgId),
      {
        name: membership.organization_name,
        country: membership.country,
        ownerUid: user.uid,
        updatedAt: serverTimestamp(),
      },
      { merge: true },
    )
    await saveFirestoreOrganizationMember(orgId, {
      uid: user.uid,
      email: user.email || profile.email,
      displayName: `${profile.first_name} ${profile.last_name}`.trim(),
      role: membership.role,
      permissions: membership.permissions,
      status: 'active',
    })
  }
}

export async function saveFirestoreOrganizationMember(
  organizationId: string,
  member: {
    uid: string
    email: string
    displayName: string
    role: string
    permissions: string[]
    status: string
  },
): Promise<void> {
  await setDoc(
    doc(getFirebaseFirestore(), 'organizations', organizationId, 'members', member.uid),
    { ...member, updatedAt: serverTimestamp() },
    { merge: true },
  )
}

export async function uploadFirebaseAvatar(file: File): Promise<string> {
  if (!file.type.startsWith('image/')) throw new Error('Sélectionnez une image.')
  if (file.size > 5 * 1024 * 1024) throw new Error('La photo ne doit pas dépasser 5 Mo.')
  const user = requireFirebaseUser()
  const extension = file.name.split('.').pop()?.toLowerCase().replace(/[^a-z0-9]/g, '') || 'jpg'
  const target = ref(getFirebaseStorage(), `avatars/${user.uid}/profile.${extension}`)
  await uploadBytes(target, file, { contentType: file.type })
  const url = await getDownloadURL(target)
  await updateProfile(user, { photoURL: url })
  return url
}

export function mapFirebaseError(err: unknown): string {
  const code = typeof err === 'object' && err && 'code' in err ? String((err as { code: string }).code) : ''
  const map: Record<string, string> = {
    'auth/invalid-email': 'Adresse email invalide.',
    'auth/user-disabled': 'Ce compte est désactivé.',
    'auth/user-not-found': 'Aucun compte avec cet email.',
    'auth/wrong-password': 'Mot de passe incorrect.',
    'auth/invalid-credential': 'Email ou mot de passe incorrect.',
    'auth/email-already-in-use': 'Cet email est déjà utilisé.',
    'auth/weak-password': 'Mot de passe trop faible (8 caractères minimum).',
    'auth/too-many-requests': 'Trop de tentatives. Réessayez plus tard.',
    'auth/requires-recent-login':
      'Pour changer le mot de passe, déconnectez-vous puis reconnectez-vous avant de réessayer.',
    'auth/network-request-failed': 'Réseau indisponible. Vérifiez votre connexion.',
    'auth/operation-not-allowed': 'Email/mot de passe non activé dans Firebase Console.',
    'storage/unauthorized':
      'Envoi de photo refusé. Publiez les règles Firebase Storage puis réessayez.',
    'storage/bucket-not-found':
      'Firebase Storage n’est pas encore activé pour ce projet.',
  }
  if (code && map[code]) return map[code]
  if (err instanceof Error && err.message) return err.message
  return 'Authentification impossible'
}
