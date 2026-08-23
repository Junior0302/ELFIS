type SectionCopyProps = {
  paragraphs: readonly string[]
}

export function SectionCopy({ paragraphs }: SectionCopyProps) {
  return (
    <>
      {paragraphs.map((text) => (
        <p key={text}>{text}</p>
      ))}
    </>
  )
}
