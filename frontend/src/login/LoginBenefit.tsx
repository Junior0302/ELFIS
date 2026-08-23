import { ElfisIcon } from '../unified-platform/icons/ElfisIconSystem'

type LoginBenefitTone = 'secure' | 'ecosystem' | 'access'

type LoginBenefitProps = {
  title: string
  text: string
  icon: string
  tone: LoginBenefitTone
}

export function LoginBenefit({ title, text, icon, tone }: LoginBenefitProps) {
  return (
    <li className="elfis-login__benefit">
      <span className={`elfis-login__benefit-icon elfis-login__benefit-icon--${tone}`} aria-hidden>
        <ElfisIcon id={icon} />
      </span>
      <div>
        <strong>{title}</strong>
        <span>{text}</span>
      </div>
    </li>
  )
}
