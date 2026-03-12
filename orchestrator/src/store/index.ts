import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { v4 as uuidv4 } from 'uuid';
import type { Proposal, ProposalStatus, ProposedAction, ChatMessage, ConnectorState, StoreData, RiskOverride, RiskLevel } from './types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const STORE_PATH = join(__dirname, '..', '..', '.store.json');

export class Store {
  private data: StoreData;

  constructor() {
    this.data = this.load();
  }

  private load(): StoreData {
    if (existsSync(STORE_PATH)) {
      const raw = readFileSync(STORE_PATH, 'utf-8');
      return JSON.parse(raw) as StoreData;
    }
    return { proposals: [], connectorStates: {}, riskOverrides: [] };
  }

  private save(): void {
    writeFileSync(STORE_PATH, JSON.stringify(this.data, null, 2));
  }

  // --- Proposals ---

  createProposal(params: {
    workflowId: string;
    workflowName: string;
    summary: string;
    actions: ProposedAction[];
    reasoning: string;
    riskLevel?: RiskLevel;
    autoApproved?: boolean;
    undoDeadline?: string;
  }): Proposal {
    const status: ProposalStatus = params.autoApproved ? 'approved' : 'pending_approval';
    const proposal: Proposal = {
      id: uuidv4(),
      workflowId: params.workflowId,
      workflowName: params.workflowName,
      summary: params.summary,
      actions: params.actions,
      reasoning: params.reasoning,
      status,
      createdAt: new Date().toISOString(),
      ...(params.riskLevel && { riskLevel: params.riskLevel }),
      ...(params.autoApproved && { autoApproved: true }),
      ...(params.autoApproved && { decidedAt: new Date().toISOString() }),
      ...(params.undoDeadline && { undoDeadline: params.undoDeadline }),
    };
    this.data.proposals.unshift(proposal);
    this.save();
    return proposal;
  }

  getProposal(id: string): Proposal | undefined {
    return this.data.proposals.find((p) => p.id === id);
  }

  listProposals(status?: ProposalStatus): Proposal[] {
    if (status) {
      return this.data.proposals.filter((p) => p.status === status);
    }
    return this.data.proposals;
  }

  hasPendingProposal(workflowId: string): boolean {
    return this.data.proposals.some(
      (p) => p.workflowId === workflowId && (p.status === 'pending_approval' || p.status === 'executing'),
    );
  }

  updateProposalStatus(id: string, status: ProposalStatus, extra?: Partial<Proposal>): Proposal | undefined {
    const proposal = this.data.proposals.find((p) => p.id === id);
    if (!proposal) return undefined;

    proposal.status = status;
    if (status === 'approved' || status === 'rejected') {
      proposal.decidedAt = new Date().toISOString();
    }
    if (extra) {
      Object.assign(proposal, extra);
    }
    this.save();
    return proposal;
  }

  appendExecutionLog(id: string, message: string): void {
    const proposal = this.data.proposals.find((p) => p.id === id);
    if (!proposal) return;
    if (!proposal.executionLog) proposal.executionLog = [];
    proposal.executionLog.push(`[${new Date().toISOString()}] ${message}`);
    this.save();
  }

  appendChatMessage(id: string, message: ChatMessage): void {
    const proposal = this.data.proposals.find((p) => p.id === id);
    if (!proposal) return;
    if (!proposal.chatHistory) proposal.chatHistory = [];
    proposal.chatHistory.push(message);
    this.save();
  }

  updateProposal(id: string, fields: Partial<Pick<Proposal, 'summary' | 'actions' | 'reasoning'>>): Proposal | undefined {
    const proposal = this.data.proposals.find((p) => p.id === id);
    if (!proposal) return undefined;
    Object.assign(proposal, fields);
    this.save();
    return proposal;
  }

  // --- Connector States ---

  getConnectorState(name: string): ConnectorState | undefined {
    return this.data.connectorStates[name];
  }

  setConnectorState(state: ConnectorState): void {
    this.data.connectorStates[state.name] = state;
    this.save();
  }

  listConnectorStates(): ConnectorState[] {
    return Object.values(this.data.connectorStates);
  }

  // --- Risk Overrides ---

  listRiskOverrides(): RiskOverride[] {
    return this.data.riskOverrides ?? [];
  }

  addRiskOverride(override: Omit<RiskOverride, 'id' | 'createdAt'>): RiskOverride {
    if (!this.data.riskOverrides) this.data.riskOverrides = [];
    const entry: RiskOverride = {
      id: uuidv4(),
      ...override,
      createdAt: new Date().toISOString(),
    };
    this.data.riskOverrides.push(entry);
    this.save();
    return entry;
  }

  removeRiskOverride(id: string): boolean {
    if (!this.data.riskOverrides) return false;
    const idx = this.data.riskOverrides.findIndex((o) => o.id === id);
    if (idx === -1) return false;
    this.data.riskOverrides.splice(idx, 1);
    this.save();
    return true;
  }
}

export function createStore(): Store {
  return new Store();
}
