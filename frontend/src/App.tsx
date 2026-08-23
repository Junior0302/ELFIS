import { Suspense, lazy, type ComponentType } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import {
  ProductThemeProvider,
  OverlayProvider,
  OverlayRouteBridge,
  isDesignSystemSandboxEnabled,
  RuntimeThemeSync,
} from './design-system'
import AuthLayout from './components/AuthLayout'
import Layout from './components/Layout'
import PlatformLayout from './components/PlatformLayout'
import DeveloperLayout from './components/DeveloperLayout'
import RequireAuth from './components/RequireAuth'
import RequirePlatformAdmin from './components/RequirePlatformAdmin'
import RequireDeveloperCockpit from './components/RequireDeveloperCockpit'
import BootstrapLoadingScreen from './platform-routing/BootstrapLoadingScreen'
import RouteChunkErrorBoundary from './platform-routing/RouteChunkErrorBoundary'
import RouteNotFound from './platform-routing/RouteNotFound'

function lazyPage(loader: () => Promise<{ default: ComponentType }>) {
  return lazy(loader)
}

const HomePage = lazyPage(() => import('./pages/HomePage'))
const ElfisHomePage = lazyPage(() => import('./home/ElfisHomePage'))
const LoginPage = lazyPage(() => import('./pages/LoginPage'))
const RegisterPage = lazyPage(() => import('./pages/RegisterPage'))
const ForgotPasswordPage = lazyPage(() => import('./pages/ForgotPasswordPage'))
const DashboardPage = lazyPage(() => import('./pages/DashboardPage'))
const DecisionsPage = lazyPage(() => import('./pages/DecisionsPage'))
const WorkQueuePage = lazyPage(() => import('./pages/WorkQueuePage'))
const DecisionDetailPage = lazyPage(() => import('./pages/DecisionDetailPage'))
const WelcomePage = lazyPage(() => import('./pages/WelcomePage'))
const EnterpriseSetupPage = lazyPage(() => import('./pages/EnterpriseSetupPage'))
const EnterpriseSetupCompanyNamePage = lazyPage(
  () => import('./pages/EnterpriseSetupCompanyNamePage'),
)
const EnterpriseSetupIndustryPage = lazyPage(() => import('./pages/EnterpriseSetupIndustryPage'))
const EnterpriseSetupCountryPage = lazyPage(() => import('./pages/EnterpriseSetupCountryPage'))
const EnterpriseSetupCurrencyPage = lazyPage(() => import('./pages/EnterpriseSetupCurrencyPage'))
const EnterpriseSetupVatPage = lazyPage(() => import('./pages/EnterpriseSetupVatPage'))
const EnterpriseSetupBankPlaceholderPage = lazyPage(
  () => import('./pages/EnterpriseSetupBankPlaceholderPage'),
)
const EnterpriseSetupSummaryPage = lazyPage(() => import('./pages/EnterpriseSetupSummaryPage'))
const EnterpriseSetupPreparationPlaceholderPage = lazyPage(
  () => import('./pages/EnterpriseSetupPreparationPlaceholderPage'),
)
const IntelligencePage = lazyPage(() => import('./pages/IntelligencePage'))
const DepositPage = lazyPage(() => import('./pages/DepositPage'))
const DocumentsPage = lazyPage(() => import('./pages/DocumentsPage'))
const VaultRedirect = lazyPage(() => import('./pages/VaultRedirect'))
const ResultPage = lazyPage(() => import('./pages/ResultPage'))
const HistoryPage = lazyPage(() => import('./pages/HistoryPage'))
const AccountingHubPage = lazyPage(() => import('./pages/AccountingHubPage'))
const AccountingProposalsPage = lazyPage(() => import('./pages/AccountingProposalsPage'))
const AccountingProposalDetailPage = lazyPage(() => import('./pages/AccountingProposalDetailPage'))
const AccountingEnginePage = lazyPage(() => import('./pages/AccountingEnginePage'))
const AccountingIntelligencePage = lazyPage(() => import('./pages/AccountingIntelligencePage'))
const SearchPage = lazyPage(() => import('./pages/SearchPage'))
const FacturationLayout = lazyPage(() => import('./comptapilot/facturation/FacturationLayout'))
const FacturationIndexRedirect = lazyPage(
  () => import('./pages/facturation/FacturationIndexRedirect'),
)
const FacturationDocumentsPage = lazyPage(
  () => import('./pages/facturation/FacturationDocumentsPage'),
)
const FacturationNouveauRedirect = lazyPage(
  () => import('./pages/facturation/FacturationNouveauRedirect'),
)
const ComposerModalRoute = lazyPage(
  () => import('./pages/facturation/ComposerModalRoute'),
)
const DevisPage = lazyPage(() => import('./pages/DevisPage'))
const ClientsPage = lazyPage(() => import('./pages/ClientsPage'))
const FournisseursPage = lazyPage(() => import('./pages/FournisseursPage'))
const CataloguePage = lazyPage(() => import('./pages/CataloguePage'))
const ActivitesPage = lazyPage(() => import('./pages/ActivitesPage'))
const AbonnementPage = lazyPage(() => import('./pages/AbonnementPage'))
const CopilotePage = lazyPage(() => import('./pages/CopilotePage'))
const ComptePage = lazyPage(() => import('./pages/ComptePage'))
const ModulesPage = lazyPage(() => import('./pages/ModulesPage'))
const MigrationPage = lazyPage(() => import('./pages/MigrationPage'))
const MigrationWizardPage = lazyPage(() => import('./pages/MigrationWizardPage'))
const NotificationsPage = lazyPage(() => import('./pages/NotificationsPage'))
const SettingsPage = lazyPage(() => import('./pages/SettingsPage'))
const PlatformSettingsPage = lazyPage(() => import('./pages/PlatformSettingsPage'))
const PlatformOrganizationPage = lazyPage(
  () => import('./pages/platform-core/PlatformOrganizationPage'),
)
const PlatformMembersPage = lazyPage(() => import('./pages/platform-core/PlatformMembersPage'))
const PlatformDocumentsHubPage = lazyPage(
  () => import('./pages/platform-core/PlatformDocumentsHubPage'),
)
const PlatformCommunicationsPage = lazyPage(
  () => import('./pages/platform-core/PlatformCommunicationsPage'),
)
const PlatformCommunicationsSettingsPage = lazyPage(
  () => import('./pages/platform-core/PlatformCommunicationsSettingsPage'),
)
const PlatformAuraPage = lazyPage(() => import('./pages/platform-core/PlatformAuraPage'))
const PlatformHelpPage = lazyPage(() => import('./pages/platform-core/PlatformHelpPage'))
const PlatformRelationsPage = lazyPage(() => import('./pages/platform-core/PlatformRelationsPage'))
const PlatformRelationDetailPage = lazyPage(
  () => import('./pages/platform-core/PlatformRelationDetailPage'),
)
const SalesDashboardPage = lazyPage(() => import('./pages/sales/SalesDashboardPage'))
const SalesIntelligencePage = lazyPage(() => import('./pages/sales/SalesIntelligencePage'))
const SalesInsightDetailPage = lazyPage(() =>
  import('./pages/sales/SalesIntelligencePage').then((m) => ({ default: m.SalesInsightDetailPage })),
)
const SalesLeadsPage = lazyPage(() => import('./pages/sales/SalesLeadsPage'))
const SalesCompaniesPage = lazyPage(() => import('./pages/sales/SalesCompaniesPage'))
const SalesContactsPage = lazyPage(() => import('./pages/sales/SalesContactsPage'))
const SalesPipelinePage = lazyPage(() => import('./pages/sales/SalesPipelinePage'))
const RelationshipWorkspacePage = lazyPage(() => import('./pages/sales/RelationshipWorkspacePage'))
const DealWorkspacePage = lazyPage(() => import('./pages/sales/DealWorkspacePage'))
const SalesProposalsPage = lazyPage(() => import('./pages/sales/SalesProposalsPage'))
const ProposalCreatePage = lazyPage(() => import('./pages/sales/ProposalCreatePage'))
const ProposalWorkspacePage = lazyPage(() => import('./pages/sales/ProposalWorkspacePage'))
const SalesTasksPage = lazyPage(() => import('./pages/sales/SalesTasksPage'))
const SalesActivitiesPage = lazyPage(() => import('./pages/sales/SalesActivitiesPage'))
const SalesCalendarPage = lazyPage(() => import('./pages/sales/SalesCalendarPage'))
const SalesImportPage = lazyPage(() => import('./pages/sales/SalesImportPage'))
const SalesJournalPage = lazyPage(() => import('./pages/sales/SalesJournalPage'))
const SalesDuplicatesPage = lazyPage(() => import('./pages/sales/SalesDuplicatesPage'))
const SalesTeamDashboardPage = lazyPage(() => import('./pages/sales/SalesTeamDashboardPage'))
const SalesCollabViewsPage = lazyPage(() => import('./pages/sales/SalesCollabViewsPage'))
const SalesReportsPage = lazyPage(() => import('./pages/sales/SalesReportsPage'))
const SalesSettingsPage = lazyPage(() => import('./pages/sales/SalesSettingsPage'))
const ReportsPage = lazyPage(() => import('./pages/ReportsPage'))
const CockpitPage = lazyPage(() => import('./pages/CockpitPage'))
const BankingPage = lazyPage(() => import('./pages/BankingPage'))
const FinancialDashboardPage = lazyPage(() => import('./pages/FinancialDashboardPage'))
const VatDeclarationPage = lazyPage(() => import('./pages/VatDeclarationPage'))
const PeriodClosePage = lazyPage(() => import('./pages/PeriodClosePage'))

const PlatformOrganizationsPage = lazyPage(() => import('./pages/platform/PlatformOrganizationsPage'))
const PlatformOrganizationDetailPage = lazyPage(
  () => import('./pages/platform/PlatformOrganizationDetailPage'),
)
const PlatformOverviewPage = lazyPage(() => import('./pages/platform/PlatformOverviewPage'))
const PlatformUsersPage = lazyPage(() => import('./pages/platform/PlatformUsersPage'))
const PlatformSubscriptionsPage = lazyPage(() => import('./pages/platform/PlatformSubscriptionsPage'))
const PlatformIncidentsPage = lazyPage(() => import('./pages/platform/PlatformIncidentsPage'))
const PlatformAuditPage = lazyPage(() => import('./pages/platform/PlatformAuditPage'))
const PlatformSecurityPage = lazyPage(() => import('./pages/platform/PlatformSecurityPage'))
const PlatformObservabilityPage = lazyPage(
  () => import('./pages/platform/PlatformObservabilityPage'),
)
const PlatformReliabilityPage = lazyPage(() => import('./pages/platform/PlatformReliabilityPage'))
const SystemHealthPage = lazyPage(() => import('./pages/platform/SystemHealthPage'))
const ActivityCenterPage = lazyPage(() => import('./pages/platform/ActivityCenterPage'))
const PlatformDocumentsPage = lazyPage(() => import('./pages/platform/PlatformDocumentsPage'))
const PlatformIntegrationsDocumentsPage = lazyPage(
  () => import('./pages/platform/PlatformIntegrationsDocumentsPage'),
)
const PlatformStoragePage = lazyPage(() => import('./pages/platform/PlatformStoragePage'))
const PlatformProcessingPage = lazyPage(() => import('./pages/platform/PlatformProcessingPage'))
const PlatformAccountingPage = lazyPage(() => import('./pages/platform/PlatformAccountingPage'))
const PlatformBankingPage = lazyPage(() => import('./pages/platform/PlatformBankingPage'))
const PlatformFinancePage = lazyPage(() => import('./pages/platform/PlatformFinancePage'))
const PlatformAiPage = lazyPage(() => import('./pages/platform/PlatformAiPage'))
const PlatformNotificationsAdminPage = lazyPage(
  () => import('./pages/platform/PlatformNotificationsAdminPage'),
)
const PlatformMigrationOpsPage = lazyPage(
  () => import('./pages/platform/PlatformMigrationOpsPage'),
)
const PlatformReportsAdminPage = lazyPage(
  () => import('./pages/platform/PlatformReportsAdminPage'),
)
const PlatformLogsPage = lazyPage(() => import('./pages/platform/PlatformLogsPage'))
const PlatformSupportPage = lazyPage(() => import('./pages/platform/PlatformSupportPage'))
const PlatformConfigurationPage = lazyPage(
  () => import('./pages/platform/PlatformConfigurationPage'),
)
const DeveloperOverviewPage = lazyPage(() => import('./pages/developer/DeveloperOverviewPage'))
const DeveloperServicesPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperServicesPage })),
)
const DeveloperApiPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperApiPage })),
)
const DeveloperWorkersPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperWorkersPage })),
)
const DeveloperJobsPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperJobsPage })),
)
const DeveloperEventsPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperEventsPage })),
)
const DeveloperLogsPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperLogsPage })),
)
const DeveloperTracesPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperTracesPage })),
)
const DeveloperDatabasePage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperDatabasePage })),
)
const DeveloperCachePage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperCachePage })),
)
const DeveloperStorageDevPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperStoragePage })),
)
const DeveloperSearchDevPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperSearchPage })),
)
const DeveloperAiDevPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperAiPage })),
)
const DeveloperNotificationsDevPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperNotificationsPage })),
)
const DeveloperFeatureFlagsPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperFeatureFlagsPage })),
)
const DeveloperConfigPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperConfigPage })),
)
const DeveloperDiagnosticsPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperDiagnosticsPage })),
)
const DeveloperAuditDevPage = lazyPage(() =>
  import('./pages/developer/DeveloperPages').then((m) => ({ default: m.DeveloperAuditPage })),
)
const ThemeSandboxPage = lazyPage(() => import('./design-system/sandbox/ThemeSandboxPage'))
const PlatformShellDemoPage = lazyPage(() => import('./pages/PlatformShellDemoPage'))

function RouteFallback() {
  return <BootstrapLoadingScreen message="Chargement de la page…" />
}

export default function App() {
  return (
    <AuthProvider>
      <ProductThemeProvider allowPreviewUnavailableProducts={false} resolveFromPath>
        <OverlayProvider>
        <BrowserRouter>
          <RuntimeThemeSync />
          <OverlayRouteBridge />
          <RouteChunkErrorBoundary>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
            {isDesignSystemSandboxEnabled() ? (
              <Route path="dev/design-system/themes" element={<ThemeSandboxPage />} />
            ) : null}
            <Route index element={<HomePage />} />
            <Route path="login" element={<LoginPage />} />
            <Route element={<AuthLayout />}>
              <Route path="register" element={<RegisterPage />} />
              <Route path="forgot-password" element={<ForgotPasswordPage />} />
            </Route>
            <Route element={<RequireAuth />}>
              <Route path="platform/shell" element={<PlatformShellDemoPage />} />
              <Route element={<Layout />}>
                <Route path="welcome" element={<WelcomePage />} />
                <Route path="home" element={<ElfisHomePage />} />
                <Route path="onboarding/entreprise" element={<EnterpriseSetupPage />} />
                <Route path="onboarding/entreprise/nom" element={<EnterpriseSetupCompanyNamePage />} />
                <Route path="onboarding/entreprise/secteur" element={<EnterpriseSetupIndustryPage />} />
                <Route path="onboarding/entreprise/pays" element={<EnterpriseSetupCountryPage />} />
                <Route path="onboarding/entreprise/devise" element={<EnterpriseSetupCurrencyPage />} />
                <Route path="onboarding/entreprise/tva" element={<EnterpriseSetupVatPage />} />
                <Route
                  path="onboarding/entreprise/banque"
                  element={<EnterpriseSetupBankPlaceholderPage />}
                />
                <Route
                  path="onboarding/entreprise/resume"
                  element={<EnterpriseSetupSummaryPage />}
                />
                <Route
                  path="onboarding/entreprise/preparation"
                  element={<EnterpriseSetupPreparationPlaceholderPage />}
                />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="sales" element={<SalesDashboardPage />} />
                <Route path="sales/intelligence" element={<SalesIntelligencePage />} />
                <Route path="sales/intelligence/:id" element={<SalesInsightDetailPage />} />
                <Route path="sales/leads" element={<SalesLeadsPage />} />
                <Route path="sales/companies" element={<SalesCompaniesPage />} />
                <Route path="sales/contacts" element={<SalesContactsPage />} />
                <Route path="sales/pipeline" element={<SalesPipelinePage />} />
                <Route path="sales/workspace/:entity/:id" element={<RelationshipWorkspacePage />} />
                <Route path="sales/deals/:id" element={<DealWorkspacePage />} />
                <Route path="sales/proposals" element={<SalesProposalsPage />} />
                <Route path="sales/proposals/new" element={<ProposalCreatePage />} />
                <Route path="sales/proposals/:id" element={<ProposalWorkspacePage />} />
                <Route path="sales/tasks" element={<SalesTasksPage />} />
                <Route path="sales/activities" element={<SalesActivitiesPage />} />
                <Route path="sales/calendar" element={<SalesCalendarPage />} />
                <Route path="sales/import" element={<SalesImportPage />} />
                <Route path="sales/journal" element={<SalesJournalPage />} />
                <Route path="sales/duplicates" element={<SalesDuplicatesPage />} />
                <Route path="sales/team" element={<SalesTeamDashboardPage />} />
                <Route path="sales/collab/views" element={<SalesCollabViewsPage />} />
                <Route path="sales/reports" element={<SalesReportsPage />} />
                <Route path="sales/settings" element={<SalesSettingsPage />} />
                <Route path="work-queue" element={<WorkQueuePage />} />
                <Route path="decisions" element={<DecisionsPage />} />
                <Route path="decisions/:decisionId" element={<DecisionDetailPage />} />
                <Route path="intelligence" element={<IntelligencePage />} />
                <Route path="deposit" element={<DepositPage />} />
                <Route path="documents" element={<DocumentsPage />} />
                <Route path="vault" element={<VaultRedirect />} />
                <Route path="result/:id" element={<ResultPage />} />
                <Route path="history" element={<HistoryPage />} />
                <Route path="accounting" element={<AccountingHubPage />} />
                <Route path="accounting/proposals" element={<AccountingProposalsPage />} />
                <Route
                  path="accounting/proposals/:proposalId"
                  element={<AccountingProposalDetailPage />}
                />
                <Route path="accounting/engine" element={<AccountingEnginePage />} />
                <Route path="accounting/intelligence" element={<AccountingIntelligencePage />} />
                <Route path="platform/banking" element={<BankingPage />} />
                <Route path="banque" element={<Navigate to="/platform/banking" replace />} />
                <Route path="banking" element={<Navigate to="/platform/banking" replace />} />
                <Route path="finance" element={<FinancialDashboardPage />} />
                <Route path="tva" element={<VatDeclarationPage />} />
                <Route path="cloture" element={<PeriodClosePage />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="cockpit" element={<CockpitPage />} />
                <Route path="facturation" element={<FacturationLayout />}>
                  <Route index element={<FacturationIndexRedirect />} />
                  <Route path="documents" element={<FacturationDocumentsPage />}>
                    <Route path="new" element={<ComposerModalRoute />} />
                  </Route>
                  <Route path="nouveau" element={<FacturationNouveauRedirect />} />
                  <Route path="catalogue" element={<Navigate to="/catalogue" replace />} />
                  <Route path="activite" element={<Navigate to="/activites" replace />} />
                </Route>
                <Route path="devis" element={<DevisPage />} />
                <Route path="quotes" element={<Navigate to="/devis" replace />} />
                <Route path="clients" element={<ClientsPage />} />
                <Route path="fournisseurs" element={<FournisseursPage />} />
                <Route path="catalogue" element={<CataloguePage />} />
                <Route path="catalog" element={<Navigate to="/catalogue" replace />} />
                <Route path="activites" element={<ActivitesPage />} />
                <Route path="abonnement" element={<AbonnementPage />} />
                <Route path="copilote" element={<CopilotePage />} />
                <Route path="organisation" element={<Navigate to="/platform/organization" replace />} />
                <Route path="admin/equipe" element={<Navigate to="/platform/members" replace />} />
                <Route path="team" element={<Navigate to="/platform/members" replace />} />
                <Route path="compte" element={<ComptePage />} />
                <Route path="modules" element={<ModulesPage />} />
                <Route path="migration" element={<MigrationPage />} />
                <Route path="migration/new" element={<MigrationWizardPage />} />
                <Route path="migration/:sessionId" element={<MigrationWizardPage />} />
                <Route path="notifications" element={<NotificationsPage />} />
                <Route path="platform/settings" element={<PlatformSettingsPage />} />
                <Route path="platform/organization" element={<PlatformOrganizationPage />} />
                <Route path="platform/members" element={<PlatformMembersPage />} />
                <Route path="platform/teams" element={<Navigate to="/platform/members" replace />} />
                <Route path="platform/roles" element={<Navigate to="/platform/members" replace />} />
                <Route path="platform/documents" element={<PlatformDocumentsHubPage />} />
                <Route path="platform/communications" element={<PlatformCommunicationsPage />} />
                <Route
                  path="platform/communications/settings"
                  element={<PlatformCommunicationsSettingsPage />}
                />
                <Route path="platform/aura" element={<PlatformAuraPage />} />
                <Route path="platform/help" element={<PlatformHelpPage />} />
                <Route path="platform/search" element={<SearchPage />} />
                <Route path="platform/relations" element={<PlatformRelationsPage />} />
                <Route
                  path="platform/relations/:relationId"
                  element={<PlatformRelationDetailPage />}
                />
                <Route path="settings" element={<SettingsPage />} />
                <Route
                  path="sales/catalog"
                  element={<Navigate to="/catalogue" replace />}
                />
                <Route path="sales/quotes" element={<Navigate to="/devis" replace />} />
              </Route>
            </Route>
            <Route element={<RequirePlatformAdmin />}>
              <Route element={<RequireDeveloperCockpit />}>
                <Route path="elfadmin/developer" element={<DeveloperLayout />}>
                  <Route index element={<DeveloperOverviewPage />} />
                  <Route path="services" element={<DeveloperServicesPage />} />
                  <Route path="api" element={<DeveloperApiPage />} />
                  <Route path="workers" element={<DeveloperWorkersPage />} />
                  <Route path="jobs" element={<DeveloperJobsPage />} />
                  <Route path="events" element={<DeveloperEventsPage />} />
                  <Route path="logs" element={<DeveloperLogsPage />} />
                  <Route path="traces" element={<DeveloperTracesPage />} />
                  <Route path="database" element={<DeveloperDatabasePage />} />
                  <Route path="cache" element={<DeveloperCachePage />} />
                  <Route path="storage" element={<DeveloperStorageDevPage />} />
                  <Route path="search" element={<DeveloperSearchDevPage />} />
                  <Route path="ai" element={<DeveloperAiDevPage />} />
                  <Route path="notifications" element={<DeveloperNotificationsDevPage />} />
                  <Route path="feature-flags" element={<DeveloperFeatureFlagsPage />} />
                  <Route path="config" element={<DeveloperConfigPage />} />
                  <Route path="diagnostics" element={<DeveloperDiagnosticsPage />} />
                  <Route path="audit" element={<DeveloperAuditDevPage />} />
                </Route>
              </Route>
              <Route path="elfadmin" element={<PlatformLayout />}>
                <Route index element={<PlatformOverviewPage />} />
                <Route path="utilisateurs" element={<PlatformUsersPage />} />
                <Route path="organisations" element={<PlatformOrganizationsPage />} />
                <Route
                  path="organisations/:organizationId"
                  element={<PlatformOrganizationDetailPage />}
                />
                <Route path="abonnements" element={<PlatformSubscriptionsPage />} />
                <Route path="migration" element={<PlatformMigrationOpsPage />} />
                <Route path="comptabilite" element={<PlatformAccountingPage />} />
                <Route path="banque" element={<PlatformBankingPage />} />
                <Route path="finance" element={<PlatformFinancePage />} />
                <Route path="ia" element={<PlatformAiPage />} />
                <Route path="notifications" element={<PlatformNotificationsAdminPage />} />
                <Route path="rapports" element={<PlatformReportsAdminPage />} />
                <Route path="logs" element={<PlatformLogsPage />} />
                <Route path="support" element={<PlatformSupportPage />} />
                <Route path="configuration" element={<PlatformConfigurationPage />} />
                <Route path="system-health" element={<SystemHealthPage />} />
                <Route path="activity" element={<ActivityCenterPage />} />
                <Route path="documents" element={<PlatformDocumentsPage />} />
                <Route path="processing" element={<PlatformProcessingPage />} />
                <Route
                  path="integrations/documents"
                  element={<PlatformIntegrationsDocumentsPage />}
                />
                <Route path="storage" element={<PlatformStoragePage />} />
                <Route path="incidents" element={<PlatformIncidentsPage />} />
                <Route path="audit" element={<PlatformAuditPage />} />
                <Route path="securite" element={<PlatformSecurityPage />} />
                <Route path="observabilite" element={<PlatformObservabilityPage />} />
                <Route path="fiabilite" element={<PlatformReliabilityPage />} />
                <Route path="emails-pro" element={<Navigate to="/elfadmin" replace />} />
              </Route>
              {/* S1.1 : /platform/* user workspace est sous Layout ; elfadmin reste la console admin */}
              <Route path="platform/admin" element={<Navigate to="/elfadmin" replace />} />
            </Route>
            {/* 404 réelle — ne pas capter les lazy routes ni renvoyer Home/Landing */}
            <Route path="*" element={<RouteNotFound />} />
          </Routes>
        </Suspense>
          </RouteChunkErrorBoundary>
        </BrowserRouter>
        </OverlayProvider>
      </ProductThemeProvider>
    </AuthProvider>
  )
}
