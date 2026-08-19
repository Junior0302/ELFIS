# 13 — SMTP runtime diagnostic

## Verdict

Au runtime local, le mailer authentifie via **SMTP Brevo** (`settings.smtp_*` issus de **`backend/.env`**). Aucune variable SMTP n’est définie dans l’environnement système du process. `email_configured=true`, transport=`smtp`. `BREVO_API_KEY` vide → pas de chemin API Brevo.

## Chargement Settings

| Élément | Valeur |
|---------|--------|
| Classe | `app.config.Settings` (`pydantic_settings.BaseSettings`) |
| `env_file` | `Path(__file__).parent.parent / ".env"` → `backend/.env` |
| Encodage | `utf-8` |
| Priorité | Variables d’environnement process **gagnent** sur `env_file` (comportement pydantic-settings par défaut) |
| Nettoyage | `smtp_user` / `smtp_password` passent par `_clean_secret` (guillemets, espaces, retours ligne) |

## Fichier `.env` chargé

| Champ | Valeur |
|-------|--------|
| Chemin absolu | `C:\Users\Black\Desktop\elfis core\backend\.env` |
| Existe | oui |
| Date de modification (locale) | `2026-08-01T18:25:50` |
| Date de modification (UTC) | `2026-08-01T16:25:50Z` |

## Variables SMTP runtime (Settings)

| Champ | Valeur affichable |
|-------|-------------------|
| `SMTP_HOST` | `smtp-relay.brevo.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `8dc723001@smtp-brevo.com` |
| `SMTP_PASSWORD` longueur | `56` |
| `SMTP_PASSWORD` préfixe (10 car.) | `xsmtpsib-2` |
| `SMTP_FROM` | vide |
| `SMTP_USE_TLS` | `true` |
| `PLATFORM_EMAIL_FROM` | `contact@elfis-core.com` (expéditeur effectif) |
| `BREVO_API_KEY` | vide / non configurée |

## Source des variables

| Variable | Présente dans process env ? | Source effective |
|----------|----------------------------|------------------|
| `SMTP_HOST` | non | **dotenv** (`backend/.env`) |
| `SMTP_PORT` | non | **dotenv** |
| `SMTP_USER` | non | **dotenv** |
| `SMTP_PASSWORD` | non | **dotenv** |
| `BREVO_API_KEY` | non | défaut vide (fichier : EMPTY) |

**Conclusion source :** toutes les credentials SMTP utilisées pour l’auth viennent du fichier dotenv, pas du system environment.

## Chemin mailer

Fichier : `backend/app/services/mailer.py`

| Flag | Valeur |
|------|--------|
| `_smtp_ready()` | `true` (host + user + password non vides) |
| `email_configured()` | `true` |
| `email_transport()` | `smtp` |
| Chemin d’auth | `_send_via_smtp` → `smtplib.SMTP(host, port)` → `starttls` si TLS → `smtp.login(user, password)` |
| Champs utilisés | `settings.smtp_host`, `settings.smtp_port`, `settings.smtp_user`, `settings.smtp_password`, `settings.smtp_use_tls` |
| Expéditeur From | `settings.effective_platform_from` (= `platform_email_from` ou `smtp_from`) → `contact@elfis-core.com` |
| Fallback API Brevo | non (clé API absente) ; SMTP tenté en premier si ready |

## Lien avec A1.1.6 (535)

La config **est lue** et jugée « configured ». L’échec runtime précédent (`Auth SMTP … 535`) concerne donc la **validité / acceptation** de cette paire login+mot de passe côté Brevo (ou filtrage IP), pas un mauvais fichier `.env` ou un override système invisible.

## Secrets

Aucun mot de passe ni clé complète n’est documenté ici — uniquement longueur et préfixe de 10 caractères pour `SMTP_PASSWORD`.
