import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, grdApi } from './api'
import type { Session } from './api'

type DocumentUploadProps = {
  session: Session
}

export default function DocumentUpload({ session }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('bank_statement')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (!file) {
      return
    }

    setSubmitting(true)
    setMessage('')

    try {
      await grdApi.uploadDocument(session.access_token, file, documentType)
      setMessage(
        'Document submitted and case created. Open Cases & Workflow to view observations.',
      )
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setMessage('Your session expired. Please sign out and log in again.')
      } else if (error instanceof Error) {
        setMessage(error.message)
      } else {
        setMessage('The document could not be submitted.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="module">
      <p className="kicker">MORE / DOCUMENT VERIFICATION</p>
      <h1>Submit a document</h1>
      <p className="muted">
        Start verification for the Phase 1 financial document categories.
      </p>

      <form className="panel upload-module" onSubmit={handleSubmit}>
        <label>
          DOCUMENT TYPE
          <select
            value={documentType}
            onChange={(event) => setDocumentType(event.target.value)}
          >
            <option value="bank_statement">Bank statement</option>
            <option value="salary_slip">Salary slip</option>
            <option value="vendor_invoice">Vendor invoice / expense bill</option>
          </select>
        </label>

        <label className="upload-box">
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <span>⇧</span>
          <b>{file?.name ?? 'Choose PDF or image'}</b>
          <small>PDF, PNG or JPEG</small>
        </label>

        {message && <p>{message}</p>}

        <button disabled={submitting}>
          {submitting ? 'Submitting…' : 'Start verification →'}
        </button>
      </form>
    </main>
  )
}
