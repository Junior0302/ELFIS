export type PartnerLogoItem = {
  id: string
  name: string
  /** URL future du logo — si absent, placeholder typographique */
  src?: string
}

type PartnerLogosProps = {
  partners: PartnerLogoItem[]
}

/**
 * Grille de logos partenaires.
 * Aujourd’hui : placeholders. Demain : renseigner `src`.
 */
export function PartnerLogos({ partners }: PartnerLogosProps) {
  return (
    <ul className="landing-partners" aria-label="Partenaires">
      {partners.map((partner) => (
        <li key={partner.id} className="landing-partners__item">
          {partner.src ? (
            <img
              src={partner.src}
              alt={partner.name}
              className="landing-partners__img"
              loading="lazy"
              decoding="async"
            />
          ) : (
            <span className="landing-partners__placeholder" title={partner.name}>
              {partner.name}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}
