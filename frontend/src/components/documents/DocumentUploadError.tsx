type Props = {
  message: string
}

export default function DocumentUploadError({ message }: Props) {
  return (
    <p className="doc-upload-error" role="alert">
      {message}
    </p>
  )
}
