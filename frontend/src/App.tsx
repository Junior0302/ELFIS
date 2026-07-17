import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import AuthLayout from './components/AuthLayout'
import Layout from './components/Layout'
import PlatformLayout from './components/PlatformLayout'
import RequireAuth from './components/RequireAuth'
import RequirePlatformAdmin from './components/RequirePlatformAdmin'
import AbonnementPage from './pages/AbonnementPage'
import ActivitesPage from './pages/ActivitesPage'
import AdminEquipePage from './pages/AdminEquipePage'
import CataloguePage from './pages/CataloguePage'
import ClientsPage from './pages/ClientsPage'
import ComptePage from './pages/ComptePage'
import CopilotePage from './pages/CopilotePage'
import DashboardPage from './pages/DashboardPage'
import DevisPage from './pages/DevisPage'
import DepositPage from './pages/DepositPage'
import FacturationPage from './pages/FacturationPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HistoryPage from './pages/HistoryPage'
import HomePage from './pages/HomePage'
import IntelligencePage from './pages/IntelligencePage'
import LoginPage from './pages/LoginPage'
import ModulesPage from './pages/ModulesPage'
import OrganisationPage from './pages/OrganisationPage'
import RegisterPage from './pages/RegisterPage'
import ResultPage from './pages/ResultPage'
import SettingsPage from './pages/SettingsPage'
import PlatformOrganizationsPage from './pages/platform/PlatformOrganizationsPage'
import PlatformOverviewPage from './pages/platform/PlatformOverviewPage'
import PlatformSubscriptionsPage from './pages/platform/PlatformSubscriptionsPage'
import PlatformUsersPage from './pages/platform/PlatformUsersPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route index element={<HomePage />} />
          <Route element={<AuthLayout />}>
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="forgot-password" element={<ForgotPasswordPage />} />
          </Route>
          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="intelligence" element={<IntelligencePage />} />
              <Route path="deposit" element={<DepositPage />} />
              <Route path="result/:id" element={<ResultPage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="facturation" element={<FacturationPage />} />
              <Route path="devis" element={<DevisPage />} />
              <Route path="clients" element={<ClientsPage />} />
              <Route path="catalogue" element={<CataloguePage />} />
              <Route path="activites" element={<ActivitesPage />} />
              <Route path="abonnement" element={<AbonnementPage />} />
              <Route path="copilote" element={<CopilotePage />} />
              <Route path="organisation" element={<OrganisationPage />} />
              <Route path="admin/equipe" element={<AdminEquipePage />} />
              <Route path="compte" element={<ComptePage />} />
              <Route path="modules" element={<ModulesPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route element={<RequirePlatformAdmin />}>
            <Route path="elfadmin" element={<PlatformLayout />}>
              <Route index element={<PlatformOverviewPage />} />
              <Route path="utilisateurs" element={<PlatformUsersPage />} />
              <Route path="organisations" element={<PlatformOrganizationsPage />} />
              <Route path="abonnements" element={<PlatformSubscriptionsPage />} />
            </Route>
            <Route path="platform" element={<Navigate to="/elfadmin" replace />} />
            <Route path="platform/*" element={<Navigate to="/elfadmin" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
