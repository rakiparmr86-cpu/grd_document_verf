import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { getApiError, grdApi } from './api'
import type { CaseDocument, CaseItem, Session } from './api'

type CasesProps = {
  session: Session
}

type ActionMessage = {
  text: string
  error: boolean
}

type CaseDocumentCardProps = {
  document: CaseDocument
  canRetry: boolean
  retrying: boolean
  onRetry: (document: CaseDocument) => void
}

function formatBytes(value: number) {
  if (value < 1024) {
    return `${value} B`
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

function readable(value: string) {
  return value
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function CaseDocumentCard({
  document,
  canRetry,
  retrying,
  onRetry,
}: CaseDocumentCardProps) {
  return (
    <article className="case-document">
      <header>
        <div>
          <b>{document.filename}</b>
          <small>
            {readable(document.document_type)} · Updated{' '}
            {new Date(document.updated_at).toLocaleString()}
          </small>
        </div>

        <div className="case-document-actions">
          <span className={`document-status ${document.status.toLowerCase()}`}>
            {readable(document.status)}
          </span>

          {canRetry && (
            <button
              type="button"
              className="retry-processing"
              disabled={retrying}
              onClick={() => onRetry(document)}
            >
              {retrying ? 'Retrying…' : 'Retry processing'}
            </button>
          )}
        </div>
      </header>

      <div className="document-facts">
        <span>Detected: {document.detected_file_type.toUpperCase()}</span>
        <span>{formatBytes(document.size_bytes)}</span>
        <span>
          {document.page_count} page{document.page_count === 1 ? '' : 's'}
        </span>
        <span>Malware: {readable(document.malware_scan_status)}</span>
        <span>
          {document.password_protected
            ? 'Password protected'
            : 'No password protection'}
        </span>
        <span className={document.storage_available ? '' : 'storage-expired'}>
          Storage: {document.storage_available ? 'Available' : 'Expired'}
        </span>
      </div>

      <ul className="document-observations">
        {document.observations.map((observation, index) => (
          <li key={`${document.id}-${index}`}>{observation}</li>
        ))}
      </ul>
    </article>
  )
}

export default function Cases({ session }: CasesProps) {
  const [cases, setCases] = useState<CaseItem[]>([])
  const [name, setName] = useState('')
  const [openCase, setOpenCase] = useState<string | null>(null)
  const [retrying, setRetrying] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<ActionMessage | null>(null)

  const loadCases = useCallback(async () => {
    try {
      const caseItems = await grdApi.getCases(session.access_token)
      setCases(caseItems)
    } catch (error) {
      const apiError = getApiError(error, 'Cases could not be loaded.')
      setActionMessage({ text: apiError.message, error: true })
    }
  }, [session.access_token])

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadCases()
    }, 0)

    const refreshTimer = window.setInterval(() => {
      void loadCases()
    }, 3000)

    return () => {
      window.clearTimeout(initialLoad)
      window.clearInterval(refreshTimer)
    }
  }, [loadCases])

  async function handleCreateCase(event: FormEvent) {
    event.preventDefault()
    setActionMessage(null)

    try {
      await grdApi.createCase(session.access_token, name)
      setName('')
      await loadCases()
    } catch (error) {
      const apiError = getApiError(error, 'The case could not be created.')
      setActionMessage({ text: apiError.message, error: true })
    }
  }

  async function handleRetry(document: CaseDocument) {
    setRetrying(document.id)
    setActionMessage(null)

    try {
      await grdApi.retryDocument(session.access_token, document.id)
      setActionMessage({
        text: `${document.filename} was queued for processing again.`,
        error: false,
      })
      await loadCases()
    } catch (error) {
      const apiError = getApiError(error, 'Retry request failed.')
      const retryText = apiError.retryAfter
        ? `${apiError.message} Try again in ${apiError.retryAfter} seconds.`
        : apiError.message

      setActionMessage({ text: retryText, error: true })
    } finally {
      setRetrying(null)
    }
  }

  function toggleCase(caseId: string) {
    setOpenCase((current) => (current === caseId ? null : caseId))
  }

  return (
    <main className="module">
      <p className="kicker">MORE / CASES & WORKFLOW</p>
      <h1>Verification cases</h1>
      <p className="muted">
        Select a case to review its documents and processing observations.
      </p>

      <form className="create-case panel" onSubmit={handleCreateCase}>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="e.g. Loan Application Case"
          required
        />
        <button>＋ Create case</button>
      </form>

      {actionMessage && (
        <p
          className={`retry-feedback ${actionMessage.error ? 'error' : 'success'}`}
        >
          {actionMessage.text}
        </p>
      )}

      <section className="panel cases-list">
        {cases.length ? (
          cases.map((caseItem) => (
            <div className="case-entry" key={caseItem.id}>
              <button
                type="button"
                className={`case-row ${openCase === caseItem.id ? 'open' : ''}`}
                onClick={() => toggleCase(caseItem.id)}
              >
                <div>
                  <b>{caseItem.name}</b>
                  <small>{caseItem.id}</small>
                </div>
                <span>
                  {caseItem.documents.length} document
                  {caseItem.documents.length === 1 ? '' : 's'}
                </span>
                <em>{caseItem.status}</em>
                <time>{new Date(caseItem.updated_at).toLocaleString()}</time>
              </button>

              {openCase === caseItem.id && (
                <div className="case-documents">
                  {caseItem.documents.length ? (
                    caseItem.documents.map((document) => {
                      const canRetry =
                        document.status === 'FAILED' &&
                        document.malware_scan_status !== 'INFECTED' &&
                        document.storage_available &&
                        session.permissions.includes('case:submit')

                      return (
                        <CaseDocumentCard
                          key={document.id}
                          document={document}
                          canRetry={canRetry}
                          retrying={retrying === document.id}
                          onRetry={handleRetry}
                        />
                      )
                    })
                  ) : (
                    <div className="case-no-documents">
                      No documents or observations are available for this case.
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="empty">
            <div>▱</div>
            <b>No cases yet</b>
            <span>Create your first multi-document case above.</span>
          </div>
        )}
      </section>
    </main>
  )
}
