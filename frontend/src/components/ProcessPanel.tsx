import type { Intent, WorkflowStep } from '../types'

type ProcessPanelProps = {
  intents: Intent[]
  authVerified: boolean
  entities: Record<string, unknown>
  workflowSteps: WorkflowStep[]
}

export function ProcessPanel(props: ProcessPanelProps) {
  const { intents, authVerified, entities, workflowSteps } = props
  const entityEntries = Object.entries(entities)

  return (
    <section className="panel">
      <h2>Processing Overview</h2>
      <div className="chipRow">
        <span className={`chip ${authVerified ? 'success' : 'warning'}`}>
          Auth: {authVerified ? 'Verified' : 'Pending / Not required'}
        </span>
      </div>

      <h3>Detected Intents</h3>
      <div className="chipRow">
        {intents.length === 0 ? (
          <span className="chip info">No intents</span>
        ) : (
          intents.map((intent) => (
            <span key={intent} className="chip info">
              {intent}
            </span>
          ))
        )}
      </div>

      <h3>Extracted Entities</h3>
      <ul className="list">
        {entityEntries.length === 0 ? (
          <li>No entities extracted yet.</li>
        ) : (
          entityEntries.map(([key, value]) => (
            <li key={key}>
              <strong>{key}:</strong> {String(value)}
            </li>
          ))
        )}
      </ul>

      <h3>Workflow Steps</h3>
      <ul className="list">
        {workflowSteps.length === 0 ? (
          <li>No steps executed yet.</li>
        ) : (
          workflowSteps.map((step, index) => (
            <li key={`${step.name}-${index}`}>
              <strong>{step.name}</strong> [{step.status}] - {step.detail}
            </li>
          ))
        )}
      </ul>
    </section>
  )
}
