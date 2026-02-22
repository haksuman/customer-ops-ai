import type { Message } from '../types'

type MailboxPanelProps = {
  threadId: string
  input: string
  messages: Message[]
  isProcessing: boolean
  onInputChange: (value: string) => void
  onThreadIdChange: (value: string) => void
  onSend: () => void
}

export function MailboxPanel(props: MailboxPanelProps) {
  const { threadId, input, messages, isProcessing, onInputChange, onThreadIdChange, onSend } = props

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
