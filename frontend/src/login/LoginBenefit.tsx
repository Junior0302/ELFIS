type LoginBenefitProps = {
  title: string
  text: string
}

export function LoginBenefit({ title, text }: LoginBenefitProps) {
  return (
    <li className="elfis-login__benefit">
      <span className="elfis-login__benefit-dot" aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <span>{text}</span>
      </div>
    </li>
  )
}
