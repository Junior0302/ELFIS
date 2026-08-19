type HomeContextCardProps = {
  label: string
  value: string
}

export function HomeContextCard({ label, value }: HomeContextCardProps) {
  return (
    <div className="home-context-card">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}
