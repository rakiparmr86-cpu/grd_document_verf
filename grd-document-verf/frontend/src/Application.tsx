import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import './Logo.css'
import './CaseDetails.css'
import { getApiError, grdApi } from './api'
import type { Session } from './api'
import BaseDashboard from './BaseDashboard'
import Cases from './Cases'
import DocumentUpload from './DocumentUpload'

type PageId =
  | 'dashboard'
  | 'documents'
  | 'cases'
  | 'reviews'
  | 'roles'
  | 'audit'
  | 'settings'

type PageSetter = (page: PageId) => void

type MoreItem = {
  id: Exclude<PageId, 'dashboard'>
  label: string
  description: string
}

const SESSION_STORAGE_KEY = 'grd_session'

const ROLE_OPTIONS = [
  { value: 'organisation_admin', label: 'Organisation Admin' },
  { value: 'verification_executive', label: 'Verification Executive' },
  { value: 'fraud_analyst', label: 'Fraud Analyst' },
  { value: 'reviewer', label: 'Reviewer' },
  { value: 'senior_approver', label: 'Senior Approver' },
  { value: 'auditor', label: 'Auditor' },
  { value: 'api_client', label: 'API Client' },
  { value: 'system_admin', label: 'System Admin' },
]

const MORE_ITEMS: MoreItem[] = [
  {
    id: 'documents',
    label: 'Document Verification',
    description: 'Upload and validate financial documents',
  },
  {
    id: 'cases',
    label: 'Cases & Workflow',
    description: 'Manage multi-document verification cases',
  },
  {
    id: 'reviews',
    label: 'Review Queue',
    description: 'Approve or reject findings',
  },
  {
    id: 'roles',
    label: 'Users & Permissions',
    description: 'Organisation roles and access',
  },
  {
    id: 'audit',
    label: 'Audit History',
    description: 'Read-only activity and status history',
  },
  {
    id: 'settings',
    label: 'System Settings',
    description: 'Organisation and infrastructure settings',
  },
]

const REQUIRED_PERMISSIONS: Partial<Record<PageId, string>> = {
  reviews: 'finding:review',
  audit: 'audit:view',
  roles: 'organisation:manage',
  settings: 'infrastructure:manage',
}

const ATTENTION_STATS = [
  ['Documents today', '0', 'Awaiting submissions', 'blue'],
  ['Cases processing', '0', 'Pipeline clear', 'cyan'],
  ['Needs review', '0', 'Analyst attention', 'orange'],
  ['High risk', '0', 'Priority follow-up', 'red'],
  ['Verified', '0', 'Completed today', 'green'],
  ['Failed', '0', 'Retry required', 'grey'],
]

const PIPELINE_STEPS = [
  'UPLOADED',
  'VALIDATING',
  'PROCESSING',
  'NEEDS REVIEW',
  'VERIFIED',
]

const AVAILABLE_PAGES = new Set<PageId>([
  'dashboard',
  ...MORE_ITEMS.map((item) => item.id),
])

function getInitialPage(): PageId {
  const requested =
    new URLSearchParams(window.location.search).get('page') ?? 'dashboard'

  return AVAILABLE_PAGES.has(requested as PageId)
    ? (requested as PageId)
    : 'dashboard'
}

function getStoredSession(): Session | null {
  try {
    return JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) ?? 'null')
  } catch {
    return null
  }
}

function Application() {
  const [session, setSession] = useState<Session | null>(getStoredSession)
  const [page, setPage] = useState<PageId>(getInitialPage)

  function handleLogin(value: Session) {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(value))
    setSession(value)
  }

  function handleLogout() {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    setSession(null)
  }

  if (!session) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <Dashboard
      session={session}
      page={page}
      setPage={setPage}
      onLogout={handleLogout}
    />
  )
}

function Login({ onLogin }: { onLogin: (session: Session) => void }) {
  const [role, setRole] = useState('verification_executive')
  const [businessType, setBusinessType] = useState('Bank')
  const [email, setEmail] = useState('abacusnikitaars@gmail.com')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const session = await grdApi.login({
        email,
        password,
        requested_role: role,
        business_type: businessType,
      })
      onLogin(session)
    } catch (submitError) {
      const apiError = getApiError(submitError, 'Sign in failed.')
      setError(apiError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <div className="login-shell">
        <section className="login-brand">
          <img
            className="reference-logo"
            src="/Artboard.png"
            alt="GRD — Getting Recruitments Done"
          />
        </section>

        <form className="login-form" onSubmit={handleSubmit}>
          <div>
            <p className="kicker">WELCOME BACK</p>
            <h2>Login to GRD Verify</h2>
            <p className="muted">Your verification command centre</p>
          </div>

          <label>
            CHOOSE ACCESS
            <select
              value={role}
              onChange={(event) => setRole(event.target.value)}
            >
              {ROLE_OPTIONS.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            BUSINESS TYPE
            <select
              value={businessType}
              onChange={(event) => setBusinessType(event.target.value)}
            >
              <option>Bank</option>
              <option>NBFC</option>
              <option>Verification Agency</option>
            </select>
          </label>

          <label>
            EMAIL ADDRESS
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              required
            />
          </label>

          <label>
            PASSWORD
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              required
              placeholder="Enter your password"
            />
          </label>

          {error && <p className="form-error">{error}</p>}

          <button disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'} <span>→</span>
          </button>

          <p className="login-help">
            Local demo: use the account matching the selected access.
          </p>
        </form>
      </div>
    </main>
  )
}

type DashboardProps = {
  session: Session
  page: PageId
  setPage: PageSetter
  onLogout: () => void
}

function Dashboard({ session, page, setPage, onLogout }: DashboardProps) {
  const [moreOpen, setMoreOpen] = useState(false)
  const formattedDate = new Date().toLocaleDateString('en-IN', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })

  function openMorePage(nextPage: MoreItem['id']) {
    setPage(nextPage)
    setMoreOpen(false)
  }

  return (
    <div className="app-shell">
      <header className="nav">
        <button className="logo" onClick={() => setPage('dashboard')}>
          <img src="/grd-header-logo.png" alt="GRD" />
        </button>

        <nav>
          <button
            onClick={() => setPage('dashboard')}
            className={page === 'dashboard' ? 'active' : ''}
          >
            ◫ Dashboard
          </button>

          <div className="more-wrap">
            <button
              className={page !== 'dashboard' ? 'active' : ''}
              onClick={() => setMoreOpen((current) => !current)}
              aria-expanded={moreOpen}
            >
              ☷ More⌄
            </button>

            {moreOpen && (
              <div className="more-menu">
                {MORE_ITEMS.map((item) => (
                  <button
                    className={page === item.id ? 'active' : ''}
                    key={item.id}
                    onClick={() => openMorePage(item.id)}
                  >
                    <b>{item.label}</b>
                    <small>{item.description}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
        </nav>

        <div className="profile">
          <span className="role-pill">{session.role.replaceAll('_', ' ')}</span>
          <button onClick={onLogout}>{session.display_name} ⌄</button>
        </div>
      </header>

      <div className="subbar">
        <span>
          Good afternoon, <b>{session.display_name}</b> — here is your document
          verification command centre.
        </span>
        <span>{formattedDate}</span>
      </div>

      {page === 'dashboard' ? (
        <Overview setPage={setPage} displayName={session.display_name} />
      ) : (
        <Module page={page} session={session} />
      )}
    </div>
  )
}

function Overview({
  setPage,
  displayName,
}: {
  setPage: PageSetter
  displayName: string
}) {
  return (
    <main className="dashboard">
      <BaseDashboard displayName={displayName} />

      <section className="verification-centre">
        <section className="welcome">
          <div>
            <p className="kicker">DOCUMENT VERIFICATION</p>
            <h1>Verification command centre</h1>
            <p>
              Monitor cases, document processing and review decisions across your
              organisation.
            </p>
          </div>
          <button onClick={() => setPage('documents')}>＋ Submit Document</button>
        </section>

        <section className="attention">
          <h3>Verification Attention</h3>
          <div className="stats">
            {ATTENTION_STATS.map(([label, value, note, tone]) => (
              <article key={label}>
                <i className={tone}>◇</i>
                <div>
                  <small>{label}</small>
                  <strong>{value}</strong>
                  <span>{note}</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <div className="dashboard-grid">
          <section className="panel">
            <div className="panel-title">
              <h3>Processing pipeline</h3>
              <button onClick={() => setPage('cases')}>View cases →</button>
            </div>

            <div className="pipeline">
              {PIPELINE_STEPS.map((step, index) => (
                <div key={step}>
                  <span>{index + 1}</span>
                  <b>{step}</b>
                  <strong>0</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-title">
              <h3>Risk distribution</h3>
            </div>
            <div className="empty">
              <div>✓</div>
              <b>No active risk signals</b>
              <span>New verification results will appear here.</span>
            </div>
          </section>
        </div>

        <section className="panel">
          <div className="panel-title">
            <h3>Recent cases</h3>
            <button onClick={() => setPage('cases')}>Open case manager →</button>
          </div>
          <div className="table-head">
            <span>CASE</span>
            <span>DOCUMENTS</span>
            <span>STATUS</span>
            <span>RISK</span>
            <span>UPDATED</span>
          </div>
          <div className="table-empty">No cases submitted in this session.</div>
        </section>
      </section>
    </main>
  )
}

function Module({
  page,
  session,
}: {
  page: Exclude<PageId, 'dashboard'>
  session: Session
}) {
  if (page === 'documents') {
    return <DocumentUpload session={session} />
  }

  if (page === 'cases') {
    return <Cases session={session} />
  }

  const item = MORE_ITEMS.find((candidate) => candidate.id === page)

  if (!item) {
    return null
  }

  const requiredPermission = REQUIRED_PERMISSIONS[page]
  const allowed =
    !requiredPermission || session.permissions.includes(requiredPermission)

  return (
    <main className="module">
      <p className="kicker">MORE / {item.label.toUpperCase()}</p>
      <h1>{item.label}</h1>
      <p className="muted">{item.description}</p>

      <section className="panel module-panel">
        {allowed ? (
          <div className="empty">
            <div>◎</div>
            <b>
              {page === 'reviews'
                ? 'No cases currently require review'
                : 'Module ready for organisation data'}
            </b>
            <span>
              This view is tenant-scoped and respects your{' '}
              {session.role.replaceAll('_', ' ')} permissions.
            </span>
          </div>
        ) : (
          <div className="denied">
            <b>Access restricted</b>
            <p>Your role does not have permission to open this module.</p>
          </div>
        )}
      </section>
    </main>
  )
}

export default Application
