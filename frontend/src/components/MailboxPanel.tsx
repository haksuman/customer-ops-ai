import type { Message, Scenario } from '../types'

type MailboxPanelProps = {
  threadId: string
  input: string
  messages: Message[]
  isProcessing: boolean
  scenarios: Scenario[]
  scenarioDescription: string
  onInputChange: (value: string) => void
  onThreadIdChange: (value: string) => void
  onSend: () => void
  onScenarioSelect: (scenario: Scenario) => void
}

export function MailboxPanel(props: MailboxPanelProps) {
  const {
    threadId,
    input,
    messages,
    isProcessing,
    scenarios,
    scenarioDescription,
    onInputChange,
    onThreadIdChange,
    onSend,
    onScenarioSelect,
  } = props

  return (
    <section className="panel">
      <h2>Customer Mailbox</h2>
      <label className="label">
        Thread ID
        <input
          value={threadId}
          onChange={(event) => onThreadIdChange(event.target.value)}
          placeholder="demo-thread-1"
        />
      </label>
      <div className="messages">
        {messages.map((message, index) => (
          <article key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
            <strong>{message.role === 'customer' ? 'Customer' : 'Assistant'}</strong>
            <p>{message.content}</p>
          </article>
        ))}
      </div>

      <div className="scenarios">
        <div className="scenario-buttons">
          {scenarios.map((s) => (
            <button key={s.id} className="scenario-btn" onClick={() => onScenarioSelect(s)}>
              {s.label}
            </button>
          ))}
        </div>
        <p className="scenario-helper">{scenarioDescription}</p>
      </div>

      <label className="label">
        New Email
        <textarea
          rows={7}
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          placeholder="Write a customer email..."
        />
      </label>
      <button disabled={isProcessing || !input.trim() || !threadId.trim()} onClick={onSend}>
        {isProcessing ? 'Processing...' : 'Process Email'}
      </button>
    </section>
  )
}
