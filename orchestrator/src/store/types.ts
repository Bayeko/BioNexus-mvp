export type ProposalStatus =
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'executing'
  | 'completed'
  | 'failed';

export type RiskLevel = 'green' | 'yellow' | 'red';

export interface ProposedAction {
  description: string;
  priority: 'high' | 'medium' | 'low';
  connector?: string;
  toolCall?: { tool: string; input: Record<string, unknown> };
  riskLevel?: RiskLevel;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface Proposal {
  id: string;
  workflowId: string;
  workflowName: string;
  summary: string;
  actions: ProposedAction[];
  reasoning: string;
  status: ProposalStatus;
  createdAt: string;
  decidedAt?: string;
  executionLog?: string[];
  chatHistory?: ChatMessage[];
  error?: string;
  riskLevel?: RiskLevel;
  autoApproved?: boolean;
  undoDeadline?: string;
}

export interface RiskOverride {
  id: string;
  pattern: string;
  riskLevel: RiskLevel;
  description?: string;
  createdAt: string;
}

export interface ConnectorState {
  name: string;
  enabled: boolean;
  configured: boolean;
  lastHealthCheck?: { ok: boolean; message?: string; checkedAt: string };
}

export interface StoreData {
  proposals: Proposal[];
  connectorStates: Record<string, ConnectorState>;
  riskOverrides: RiskOverride[];
}
