import './BaseDashboard.css'

type Metric = {
  icon: string
  label: string
  value: string
  note: string
  tone: 'blue' | 'cyan' | 'green' | 'orange' | 'red' | 'grey'
}

const recruiterMetrics: Metric[] = [
  {
    icon: '▣',
    label: "My Task's",
    value: '5',
    note: 'Carry Forward',
    tone: 'blue',
  },
  {
    icon: '▰',
    label: 'My Jobs',
    value: '0',
    note: 'Action Pending',
    tone: 'cyan',
  },
  {
    icon: '⌁',
    label: 'CV Target v/s Achieved',
    value: '0 / 0',
    note: 'Yesterday Backlog',
    tone: 'green',
  },
  {
    icon: '▦',
    label: "Interview's Today",
    value: '0',
    note: 'Feedback Pending',
    tone: 'orange',
  },
  {
    icon: '♙',
    label: 'My Prospects',
    value: '2',
    note: 'Critical Follow-Up',
    tone: 'red',
  },
  {
    icon: '♧',
    label: "Today's Joining",
    value: '0',
    note: 'Confirmation',
    tone: 'green',
  },
  {
    icon: '▤',
    label: 'Notes',
    value: '0',
    note: 'Unresolved Notes',
    tone: 'grey',
  },
]

const rraMetrics: Metric[] = [
  { icon: '▥', label: 'Active Clients', value: '261', note: 'Client Follow-Up', tone: 'blue' },
  { icon: '▰', label: 'Active Job', value: '0', note: 'Priority Jobs', tone: 'green' },
  { icon: '▣', label: 'Assigned Jobs', value: '0', note: 'Jobs Assigned', tone: 'orange' },
  { icon: '▥', label: 'Unassigned Jobs', value: '0', note: 'Urgent', tone: 'blue' },
  { icon: '⊕', label: 'New Jobs', value: '0', note: 'To Assign', tone: 'blue' },
  { icon: '♙', label: 'Prospects', value: '13', note: 'Follow-up Due', tone: 'cyan' },
  { icon: '▣', label: 'Pending Client Feedback', value: '38', note: 'Overdue', tone: 'orange' },
  { icon: '♟', label: 'Stuck Follow-Ups', value: '9', note: 'Candidates / Client', tone: 'grey' },
  { icon: '♟', label: 'Met Candidate Feedback', value: '0', note: 'New today', tone: 'grey' },
  { icon: '▦', label: "Interview's Scheduled", value: '0', note: 'Feedback Due', tone: 'red' },
  { icon: '♧', label: "Today's Joining", value: '0', note: 'Joining Due', tone: 'green' },
]

const taskTabs = [
  ['Summary', ''],
  ['Today', '5'],
  ['Overdue', '31'],
  ['Upcoming', '2'],
  ['Some Day May Be', '2'],
  ['Waiting For', '17'],
  ['Routine', '19'],
  ['Team', '2'],
  ['WOW Feedback', '8'],
  ['References', '3'],
]

function MetricCard({ metric }: { metric: Metric }) {
  return (
    <article className="base-metric">
      <span className={`base-metric-icon ${metric.tone}`}>{metric.icon}</span>
      <span className="base-metric-copy">
        <small>{metric.label}</small>
        <strong>{metric.value}</strong>
        <em className={metric.tone}>{metric.note}</em>
      </span>
    </article>
  )
}

const planSteps = [
  { label: 'Today’s Planning', note: 'Plan your priorities' },
  { label: 'During Day Control', note: 'Track and take action' },
  { label: 'Evening Review', note: 'Review and reflect' },
  { label: 'Prepare Tomorrow', note: 'Plan ahead' },
]

export default function BaseDashboard({ displayName }: { displayName: string }) {
  const date = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })

  return (
    <section className="base-dashboard" aria-label="Recruiter command dashboard">
      <div className="base-greeting">
        <span className="base-moon">◔</span>
        <b>Good Afternoon {displayName}!</b>
        <small>Here&apos;s your recruiter command center for today.</small>
        <div className="base-scope">
          <button className="active">♙ Self</button>
          <button>♙ Team</button>
          <button>▥ Organisation</button>
        </div>
        <time>▦ {date}</time>
      </div>

      <div className="base-command-row">
        <div className="base-plan-steps">
          {planSteps.map((step, index) => (
            <div className={index === 0 ? 'active' : ''} key={step.label}>
              <span>{index + 1}</span>
              <p>
                <b>{step.label}</b>
                <small>{step.note}</small>
              </p>
            </div>
          ))}
        </div>
        <div className="base-modes">
          <button className="active">▣ Command</button>
          <button>☷ Control</button>
          <button>⌁ Insight</button>
        </div>
      </div>

      <section className="base-panel">
        <h2>Recruiter Attention</h2>
        <div className="base-metric-grid recruiter">
          {recruiterMetrics.map((metric) => (
            <MetricCard metric={metric} key={metric.label} />
          ))}
        </div>
      </section>

      <section className="base-panel">
        <h2>RRA Attention</h2>
        <div className="base-metric-grid rra">
          {rraMetrics.map((metric) => (
            <MetricCard metric={metric} key={metric.label} />
          ))}
        </div>
      </section>

      <section className="base-panel base-priority">
        <header>
          <h2>
            <span>◉</span> Today&apos;s Priority Tasks
          </h2>
          <button>Make a Note</button>
        </header>

        <div className="base-task-tabs">
          {taskTabs.map(([label, count], index) => (
            <button className={index === 0 ? 'active' : ''} key={label}>
              {label}
              {count && <span>{count}</span>}
            </button>
          ))}
        </div>

        <div
          className="base-task-table"
          role="table"
          aria-label="Today's priority tasks"
        >
          <div className="base-task-row header">
            <b>Name</b>
            <b>Urgent</b>
            <b>Important</b>
            <b>Regular</b>
            <b>Total</b>
          </div>
          <div className="base-task-row">
            <b>Siddhi Gupta</b>
            <span className="red">● ● ○</span>
            <span className="orange">● ● ○</span>
            <span className="green">● ● ○</span>
            <span className="cyan">● ● ○</span>
          </div>
          <div className="base-task-row total">
            <b>Total</b>
            <b>0 - 0 - 0</b>
            <b>0 - 0 - 0</b>
            <b>2 - 0 - 2</b>
            <b>2 - 0 - 2</b>
          </div>
        </div>
      </section>

      <section className="base-panel base-jobs">
        <h2>
          <span>▰</span> My Jobs
        </h2>
      </section>
    </section>
  )
}
