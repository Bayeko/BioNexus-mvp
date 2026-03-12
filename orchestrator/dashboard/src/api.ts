const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// --- Types matching server ---

export type RiskLevel = 'green' | 'yellow' | 'red';

export interface ProposedAction {
  description: string;
  priority: 'high' | 'medium' | 'low';
  connector?: string;
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
  status: string;
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

export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: { type: string; cron?: string; event?: string };
  instruction: string;
  requiredConnectors: string[];
  source: 'builtin' | 'user-created';
}

export interface ConnectorInfo {
  name: string;
  displayName: string;
  description: string;
  toolCount: number;
  enabled: boolean;
  configured: boolean;
  lastHealthCheck?: { ok: boolean; message?: string; checkedAt: string };
}

// --- API functions ---

export const api = {
  getHealth: () => request<{ status: string; uptime: number }>('/health'),
  getProposals: () => request<Proposal[]>('/proposals'),
  approveProposal: (id: string) => request<Proposal>(`/proposals/${id}/approve`, { method: 'POST' }),
  rejectProposal: (id: string, reason?: string) =>
    request<Proposal>(`/proposals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  chatWithProposal: (id: string, message: string) =>
    request<{ reply: string; chatHistory: ChatMessage[] }>(`/proposals/${id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  reviseProposal: (id: string) =>
    request<Proposal>(`/proposals/${id}/revise`, { method: 'POST' }),
  getWorkflows: () => request<WorkflowDefinition[]>('/workflows'),
  toggleWorkflow: (id: string) => request<WorkflowDefinition>(`/workflows/${id}/toggle`, { method: 'PUT' }),
  triggerWorkflow: (id: string) => request<{ ok: boolean }>(`/workflows/${id}/trigger`, { method: 'POST' }),
  deleteWorkflow: (id: string) => request<{ ok: boolean }>(`/workflows/${id}`, { method: 'DELETE' }),
  createWorkflowFromPrompt: (prompt: string) =>
    request<WorkflowDefinition>('/workflows/create-from-prompt', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),
  undoProposal: (id: string) => request<Proposal>(`/proposals/${id}/undo`, { method: 'POST' }),
  getConnectors: () => request<ConnectorInfo[]>('/connectors'),
  enableConnector: (name: string) => request<unknown>(`/connectors/${name}/enable`, { method: 'PUT' }),
  disableConnector: (name: string) => request<unknown>(`/connectors/${name}/disable`, { method: 'PUT' }),
  getRiskOverrides: () => request<RiskOverride[]>('/settings/risk-overrides'),
  addRiskOverride: (override: { pattern: string; riskLevel: RiskLevel; description?: string }) =>
    request<RiskOverride>('/settings/risk-overrides', {
      method: 'POST',
      body: JSON.stringify(override),
    }),
  removeRiskOverride: (id: string) =>
    request<{ ok: boolean }>(`/settings/risk-overrides/${id}`, { method: 'DELETE' }),
};

// --- SSE ---

export type SSEEventHandler = (event: string, data: unknown) => void;

export function connectSSE(onEvent: SSEEventHandler): EventSource {
  const es = new EventSource(`${BASE}/sse`);

  es.addEventListener('connected', (e) => {
    onEvent('connected', JSON.parse(e.data));
  });

  es.addEventListener('proposal:created', (e) => {
    onEvent('proposal:created', JSON.parse(e.data));
  });

  es.addEventListener('proposal:updated', (e) => {
    onEvent('proposal:updated', JSON.parse(e.data));
  });

  es.addEventListener('workflow:created', (e) => {
    onEvent('workflow:created', JSON.parse(e.data));
  });

  es.addEventListener('workflow:updated', (e) => {
    onEvent('workflow:updated', JSON.parse(e.data));
  });

  es.addEventListener('workflow:deleted', (e) => {
    onEvent('workflow:deleted', JSON.parse(e.data));
  });

  es.addEventListener('connector:updated', (e) => {
    onEvent('connector:updated', JSON.parse(e.data));
  });

  es.onerror = () => {
    onEvent('error', { message: 'SSE connection lost' });
  };

  return es;
}
