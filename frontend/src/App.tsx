import { useMemo, useState } from 'react'
import './App.css'
import { MailboxPanel } from './components/MailboxPanel'
import { ProcessPanel } from './components/ProcessPanel'
import type { Message, ProcessResponse } from './types'

function App() {
  const [threadId, setThreadId] = useState('demo-thread-1')
  const [input, setInput] = useState(
    "Hello LichtBlick Team,\n\nI'd like to submit my latest electricity meter reading and ask about your dynamic tariff. My contract number is LB-9876543 and the reading is 1438 kWh.\n\nMy postal code is 20097.\n\nBest regards,\nJulia Meyer",
  );
  const [messages, setMessages] = useState<Message[]>([])
  const [lastResult, setLastResult] = useState<ProcessResponse | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const apiBaseUrl = useMemo(
    () => import.meta.env.VITE_API_URL?.toString() || 'http://localhost:8000',
    []
  )

  const handleSend = async () => {
    setIsProcessing(true)
    try {
      const payload = { thread_id: threadId, message: input }
      setMessages((prev) => [...prev, { role: 'customer', content: input }])
      setInput('')

      const response = await fetch(`${apiBaseUrl}/api/messages/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`)
      }
      const data = (await response.json()) as ProcessResponse
      setLastResult(data)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.assistant_reply }])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Request failed: ${(error as Error).message}` },
      ])
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <main className="layout">
      <header>
        <h1>Agentic Customer Copilot</h1>
        <p>Email handling demo with transparent workflow execution.</p>
      </header>
      <div className="grid">
        <MailboxPanel
          threadId={threadId}
          input={input}
          messages={messages}
          isProcessing={isProcessing}
          onInputChange={setInput}
          onThreadIdChange={setThreadId}
          onSend={handleSend}
        />
        <ProcessPanel
          intents={lastResult?.intents ?? []}
          authVerified={lastResult?.auth_verified ?? false}
          entities={lastResult?.entities ?? {}}
          workflowSteps={lastResult?.workflow_steps ?? []}
        />
      </div>
    </main>
  )
}

export default App
