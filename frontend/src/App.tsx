import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import AuthLayout from './components/AuthLayout'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import ComptePage from './pages/ComptePage'
import CopilotePage from './pages/CopilotePage'
import DashboardPage from './pages/DashboardPage'
import DepositPage from './pages/DepositPage'
import FacturationPage from './pages/FacturationPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HistoryPage from './pages/HistoryPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import ModulesPage from './pages/ModulesPage'
import OrganisationPage from './pages/OrganisationPage'
import RegisterPage from './pages/RegisterPage'
import ResultPage from './pages/ResultPage'
import SettingsPage from './pages/SettingsPage'

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
              <Route path="deposit" element={<DepositPage />} />
              <Route path="result/:id" element={<ResultPage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="facturation" element={<FacturationPage />} />
              <Route path="copilote" element={<CopilotePage />} />
              <Route path="organisation" element={<OrganisationPage />} />
              <Route path="compte" element={<ComptePage />} />
              <Route path="modules" element={<ModulesPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
