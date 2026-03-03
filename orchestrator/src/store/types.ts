export type ProposalStatus =
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'executing'
  | 'completed'
  | 'failed';

export interface ProposedAction {
  description: string;
  priority: 'high' | 'medium' | 'low';
  connector?: string;
  toolCall?: { tool: string; input: Record<string, unknown> };
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
  error?: string;
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
}
