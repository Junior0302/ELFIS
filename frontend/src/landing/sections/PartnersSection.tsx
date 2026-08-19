import { PartnerLogos, type PartnerLogoItem } from '../components/PartnerLogos'

/** Logos fictifs — remplacer `src` quand les fichiers sont prêts. */
const PARTNERS: PartnerLogoItem[] = [
  { id: 'nordica', name: 'Nordica' },
  { id: 'atelier', name: 'Atelier Vert' },
  { id: 'helix', name: 'Helix Soft' },
  { id: 'lumen', name: 'Lumen Ops' },
  { id: 'harbor', name: 'Harbor Group' },
  { id: 'pulse', name: 'Pulse Lab' },
]

export function PartnersSection() {
  return (
    <section className="landing-section landing-partners-section" aria-labelledby="landing-partners-title">
      <div className="landing-section__intro landing-section__intro--center">
        <p className="landing-kicker">Partenaires</p>
        <h2 id="landing-partners-title">Ils construisent avec ELFIS</h2>
        <p className="landing-section__lead">
          Emplacements logos — assets fictifs aujourd’hui, remplacement sans refactor.
        </p>
      </div>
      <PartnerLogos partners={PARTNERS} />
    </section>
  )
}
