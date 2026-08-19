import { WorkflowTimeline } from '../components/WorkflowTimeline'

const STEPS = [
  {
    id: 'prospect',
    label: 'Prospect',
    description: 'Capturez et qualifiez les contacts entrants.',
  },
  {
    id: 'opportunity',
    label: 'Opportunité',
    description: 'Suivez le pipeline dans SalesPilot.',
  },
  {
    id: 'proposal',
    label: 'Proposition',
    description: 'Construisez et envoyez une offre claire.',
  },
  {
    id: 'contract',
    label: 'Contrat signé',
    description: 'Documentez l’accord et le contexte.',
  },
  {
    id: 'invoice',
    label: 'Facture',
    description: 'Passez en ComptaPilot sans ressaisie.',
  },
  {
    id: 'payment',
    label: 'Paiement',
    description: 'Suivez l’encaissement jusqu’à clôture.',
  },
]

export function WorkflowSection() {
  return (
    <section id="solutions" className="landing-section landing-workflow" aria-labelledby="landing-workflow-title">
      <div className="landing-section__intro">
        <p className="landing-kicker">Workflow connecté</p>
        <h2 id="landing-workflow-title">Du prospect au paiement</h2>
        <p className="landing-section__lead">
          Un parcours métier fluide entre SalesPilot et ComptaPilot — les données circulent,
          le Pilot Mark reste stable.
        </p>
      </div>
      <WorkflowTimeline steps={STEPS} />
    </section>
  )
}
