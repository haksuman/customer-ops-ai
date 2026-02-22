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
