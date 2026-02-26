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
  requires_manual_review?: boolean
  manual_review_reason?: string
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

export type NotHandledEmail = {
  id: string
  thread_id: string
  original_message: string
  detected_intents: Intent[]
  reason_code: string
  ai_log: string
  created_at: string
  status: 'pending' | 'resolved'
}

export type DashboardKpis = {
  total_processed: number
  auto_handled: number
  manual_forwarded: number
  approvals: number
  rejections: number
  automation_rate: number
}

export type DashboardTimeseriesPoint = {
  date: string
  processed: number
  auto_handled: number
  manual_forwarded: number
}

export type DashboardIntentBreakdown = {
  intent: string
  count: number
}

export type DashboardReasonBreakdown = {
  reason: string
  count: number
}

export type DashboardResponse = {
  kpis: DashboardKpis
  timeseries: DashboardTimeseriesPoint[]
  intents: DashboardIntentBreakdown[]
  reasons: DashboardReasonBreakdown[]
}
