# ELFIS Core — Agent Handoff

## Project identity

ELFIS Core is the parent business platform.
ComptaPilot is one of its main products/modules.

The repository contains a FastAPI backend and a React/TypeScript frontend.

The goal is to build a production-grade modular SaaS platform capable of supporting more than 1,000 customers.

## Core development principles

- Do not rewrite working architecture without first understanding existing contracts.
- Prefer incremental, backward-compatible changes.
- Preserve tenant/organization isolation.
- Preserve auditability for sensitive operations.
- Never weaken authentication, authorization, billing, accounting, document security, or operational controls merely to simplify implementation.
- Do not introduce fake production behavior.
- Clearly distinguish production logic from development/test fallbacks.
- Reuse existing domain services and platform primitives before creating duplicate systems.
- Run relevant tests after modifications.
- Keep documentation synchronized with major architectural changes.

## Existing platform areas

The codebase already includes or has work relating to:

- Authentication and organization/workspace flows
- ELFIS Vault
- Event Bus / Outbox
- Notifications
- Durable Job Queue
- AI Engine
- Document Intelligence
- Accounting Pipeline
- Search Engine
- Stripe billing and trial flows
- Platform Admin / Ops
- Security / observability / resilience
- System Health
- Financial dashboards
- Migration tooling
- Platform Shell
- Unified Design System
- App Launcher
- Global Search
- Command Center
- ComptaPilot billing/document creation
- SalesPilot CRM and sales workflows
- Resource Library
- Insight Framework
- Workspace provisioning

## Repository structure

- backend/ : FastAPI backend
- frontend/ : React + TypeScript frontend
- docs/ : platform/project documentation
- scripts/ : development and operational scripts
- comptapilot.db : local development database
- render.yaml : deployment configuration
- firebase.json / firestore.* : Firebase configuration

## Before implementing

Before modifying a subsystem:

1. Inspect the relevant implementation.
2. Inspect existing tests.
3. Inspect related documentation.
4. Identify existing domain contracts and shared primitives.
5. Avoid creating a second source of truth.

## Database changes

For schema changes:

- use the existing migration system
- keep migrations forward-safe
- preserve existing data
- do not manually mutate production schema
- test upgrade paths where relevant

## Frontend

Prefer the existing ELFIS design system, unified platform primitives, platform shell, theme engine and product registries instead of isolated visual implementations.

Preserve responsive behavior and accessibility.

## Backend

Prefer existing services, repositories, domain boundaries and event/job infrastructure.

Sensitive mutations must respect authentication, authorization, tenant boundaries and audit requirements.

## AI behavior

AI features must not silently invent accounting, financial or operational facts.

Distinguish extracted facts, inferred data, confidence and missing information.

Human validation must remain available for consequential actions.

## Operational rule

Never deploy, migrate production data, rotate secrets or make destructive infrastructure changes without an explicit verification step.

## Git

Main development branch is currently `main`.

Git remote:
https://github.com/Junior0302/ELFIS.git

Do not rewrite Git history unless explicitly required.

## Handoff

Historical Cursor Agent transcripts have been archived separately during the account migration.

When uncertain about a previous architectural decision, inspect repository documentation and Git history before replacing existing behavior.
