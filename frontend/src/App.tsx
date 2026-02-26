import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import './App.css'
import { MailboxPanel } from './components/MailboxPanel'
import { ProcessPanel } from './components/ProcessPanel'
import type { Message, ProcessResponse, Scenario } from './types'

const SCENARIOS: Scenario[] = [
  {
    id: 'full-success',
    label: 'Prompt 1',
    description: 'Full Success: Complete auth + Meter reading + Tariff question.',
    text: "Hello LichtBlick Team,\n\nI'd like to submit my latest electricity meter reading and ask about your dynamic tariff. My contract number is LB-9876543 and the reading is 1438 kWh.\n\nMy postal code is 20097.\n\nBest regards,\nJulia Meyer",
  },
  {
    id: 'missing-data',
    label: 'Prompt 2',
    description: 'Missing Data: Meter reading provided but missing postal code.',
    text: "Hello,\n\nI am Hans Müller (Contract LB-1122334). My meter reading is 950 kWh.\n\nThanks.",
  },
  {
    id: 'anomaly',
    label: 'Prompt 3',
    description: 'Anomaly: Valid auth but unusually high meter reading.',
    text: "Dear Team,\n\nI'm Anna Schmidt, living in 80331. My contract number is LB-5566778. I want to report my meter reading as 4500 kWh.\n\nBest, Anna.",
  },
  {
    id: 'pure-query',
    label: 'Prompt 4',
    description: 'Pure Query: Only asking about tariffs (No authentication required).',
    text: "Hi! Can you tell me more about your dynamic tariff? How does it work and what are the benefits?",
  },
  {
    id: 'data-change',
    label: 'Prompt 5',
    description: 'Data Change: Requesting a name change (Requires authentication).',
    text: "Hello LichtBlick,\n\nI'm Thomas Wagner (Contract LB-9900112, PLZ 60313). I've recently got married and would like to change my name on the contract to Thomas Müller.\n\nRegards,\nThomas Wagner",
  },
  {
    id: 'out-of-scope',
    label: 'Prompt 6',
    description: 'Out of Scope: Asking for tax advice (Should be forwarded).',
    text: "Dear LichtBlick,\n\nI'm happy with my electricity contract, but I have a question about my income tax declaration. Do I need to report the solar feed-in tariff as income? If so, which form do I use?\n\nBest regards,\nMax Mustermann",
  },
  {
    id: 'complex-request',
    label: 'Prompt 7',
    description: 'Complex Request: Hardware issue + Scheduling (Should be forwarded).',
    text: "Hello,\n\nMy smart meter (LB-123456) is making a loud buzzing sound and seems very hot. I'm worried it might be a fire hazard. Can someone come and check it today? I'm home until 4 PM.\n\nThanks,\nErika Schmidt",
  },
]

function App() {
  const [threadId, setThreadId] = useState('demo-thread-1')
  const [input, setInput] = useState(SCENARIOS[0].text)
  const [scenarioDescription, setScenarioDescription] = useState(SCENARIOS[0].description)
  const [messages, setMessages] = useState<Message[]>([])
  const [lastResult, setLastResult] = useState<ProcessResponse | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const apiBaseUrl = useMemo(
    () => import.meta.env.VITE_API_URL?.toString() || 'http://localhost:8000',
    []
  )

  const handleScenarioSelect = (scenario: Scenario) => {
    setInput(scenario.text)
    setScenarioDescription(scenario.description)
  }

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
      <nav className="nav">
        <Link to="/" className="nav-link active">Customer Portal</Link>
        <Link to="/operator" className="nav-link">Operator Dashboard</Link>
        <Link to="/not-handled" className="nav-link">Not Handled Emails</Link>
        <Link to="/dashboard" className="nav-link">Manager Dashboard</Link>
      </nav>
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
          scenarios={SCENARIOS}
          scenarioDescription={scenarioDescription}
          onInputChange={setInput}
          onThreadIdChange={setThreadId}
          onSend={handleSend}
          onScenarioSelect={handleScenarioSelect}
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
