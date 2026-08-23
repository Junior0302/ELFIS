import { useAuth } from '../auth'
import { AudiencesSection } from './sections/AudiencesSection'
import { BrandSection } from './sections/BrandSection'
import { ContinuitySection } from './sections/ContinuitySection'
import { FinalCtaSection } from './sections/FinalCtaSection'
import { Footer } from './sections/Footer'
import { HeroSection } from './sections/HeroSection'
import { HorizonSection } from './sections/HorizonSection'
import { IntelligenceSection } from './sections/IntelligenceSection'
import { Navbar } from './sections/Navbar'
import { PlatformSection } from './sections/PlatformSection'
import { ProblemSection } from './sections/ProblemSection'
import { SecuritySection } from './sections/SecuritySection'
import { SpacesShowcaseSection } from './sections/SpacesShowcaseSection'
import './landing.css'

/**
 * Page d’accueil publique ELFIS Core.
 * Thème plateforme via route `/` → RuntimeThemeSync (elfis-core).
 */
export function LandingPage() {
  const { user } = useAuth()
  const isAuthenticated = Boolean(user)

  return (
    <div className="landing">
      <div className="landing__atmosphere" aria-hidden>
        <span className="landing__orb landing__orb--blue" />
        <span className="landing__orb landing__orb--navy" />
        <span className="landing__orb landing__orb--mint" />
        <span className="landing__grid" />
      </div>
      <Navbar isAuthenticated={isAuthenticated} />
      <main id="contenu-principal">
        <HeroSection isAuthenticated={isAuthenticated} />
        <ProblemSection />
        <PlatformSection />
        <SpacesShowcaseSection />
        <ContinuitySection />
        <AudiencesSection />
        <IntelligenceSection />
        <SecuritySection />
        <HorizonSection />
        <BrandSection />
        <FinalCtaSection isAuthenticated={isAuthenticated} />
      </main>
      <Footer isAuthenticated={isAuthenticated} />
    </div>
  )
}
