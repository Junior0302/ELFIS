import { useAuth } from '../auth'
import { ApplicationsSection } from './sections/ApplicationsSection'
import { BenefitsSection } from './sections/BenefitsSection'
import { CTASection } from './sections/CTASection'
import { FeaturesSection } from './sections/FeaturesSection'
import { Footer } from './sections/Footer'
import { HeroSection } from './sections/HeroSection'
import { Navbar } from './sections/Navbar'
import { PartnersSection } from './sections/PartnersSection'
import { WorkflowSection } from './sections/WorkflowSection'
import './landing.css'

/**
 * Landing officielle ELFIS Core V1 (LAND-CEB).
 * Thème plateforme via route `/` → RuntimeThemeSync (elfis-core).
 */
export function LandingPage() {
  const { user } = useAuth()
  const primaryTo = user ? '/home' : '/register'
  const loginTo = '/login'

  return (
    <div className="landing">
      <Navbar primaryTo={primaryTo} loginTo={loginTo} isAuthenticated={Boolean(user)} />
      <main id="contenu-principal">
        <HeroSection primaryTo={primaryTo} secondaryTo={loginTo} isAuthenticated={Boolean(user)} />
        <ApplicationsSection />
        <WorkflowSection />
        <BenefitsSection />
        <PartnersSection />
        <FeaturesSection />
        <CTASection primaryTo={primaryTo} secondaryTo={loginTo} isAuthenticated={Boolean(user)} />
      </main>
      <Footer />
    </div>
  )
}
