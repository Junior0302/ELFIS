import type { FormEvent, RefObject } from 'react'
import { Link } from 'react-router-dom'
import { Button, FormField, Input } from '../design-system'

type LoginFormProps = {
  email: string
  password: string
  loading: boolean
  disabled: boolean
  error: string
  errorRef: RefObject<HTMLDivElement | null>
  onEmailChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onSubmit: (e: FormEvent) => void
  forgotPasswordTo: string
}

export function LoginForm({
  email,
  password,
  loading,
  disabled,
  error,
  errorRef,
  onEmailChange,
  onPasswordChange,
  onSubmit,
  forgotPasswordTo,
}: LoginFormProps) {
  return (
    <form className="elfis-login__form" onSubmit={onSubmit} noValidate={false}>
      <FormField label="Email" htmlFor="elfis-login-email" required>
        <Input
          id="elfis-login-email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          placeholder="vous@entreprise.com"
          value={email}
          onChange={(e) => onEmailChange(e.target.value)}
          required
          disabled={loading || disabled}
        />
      </FormField>

      <div className="elfis-login__password-block">
        <div className="elfis-login__password-heading">
          <label htmlFor="elfis-login-password">
            Mot de passe <span className="ds-form-field__required" aria-hidden> *</span>
          </label>
          <Link to={forgotPasswordTo}>Mot de passe oublié ?</Link>
        </div>
        <Input
          id="elfis-login-password"
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="Votre mot de passe"
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
          required
          disabled={loading || disabled}
          aria-describedby={error ? 'elfis-login-error' : undefined}
          aria-invalid={error ? true : undefined}
        />
      </div>

      {error ? (
        <div
          id="elfis-login-error"
          ref={errorRef}
          className="elfis-login__alert"
          role="alert"
          aria-live="assertive"
          tabIndex={-1}
        >
          {error}
        </div>
      ) : null}

      <Button
        className="elfis-login__submit"
        type="submit"
        disabled={loading || disabled}
        aria-busy={loading || undefined}
      >
        {loading ? 'Connexion…' : 'Se connecter'}
      </Button>
    </form>
  )
}
