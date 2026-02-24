export type Intent =
  | 'MeterReadingSubmission'
  | 'PersonalDataChange'
  | 'ContractIssues'
  | 'ProductInfoRequest'
  | 'GeneralFeedback'

export type WorkflowStep = {
  name: string
  status: 'pending' | 'running' | 'completed' | 'skipped' | 'failed'
  detail: string
}

export type Message = {
  role: 'customer' | 'assistant'
  content: string
}

export type ProcessResponse = {
  thread_id: string
  assistant_reply: string
  intents: Intent[]
  auth_verified: boolean
  entities: Record<string, unknown>
  workflow_steps: WorkflowStep[]
}

export type Scenario = {
  id: string
  label: string
  text: string
  description: string
}

export type PendingApproval = {
  id: string
  thread_id: string
  contract_number: string
  intent: Intent
  requested_change: Record<string, unknown>
  ai_summary: string
  is_dangerous: boolean
  created_at: string
  customer_info?: Record<string, unknown>
}
