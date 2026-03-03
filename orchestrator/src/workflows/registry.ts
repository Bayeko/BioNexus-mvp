import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { WorkflowDefinition } from './types.js';
import { morningKickoff } from './builtin/morning-kickoff.js';
import { crossAgentSync } from './builtin/cross-agent-sync.js';
import { meetingPrep } from './builtin/meeting-prep.js';
import { weeklyReview } from './builtin/weekly-review.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const WORKFLOWS_PATH = join(__dirname, '..', '..', '.workflows.json');

const BUILTIN_WORKFLOWS: WorkflowDefinition[] = [
  morningKickoff,
  crossAgentSync,
  meetingPrep,
  weeklyReview,
];

export class WorkflowRegistry {
  private workflows: Map<string, WorkflowDefinition> = new Map();

  constructor() {
    this.loadBuiltins();
    this.loadUserWorkflows();
  }

  private loadBuiltins(): void {
    for (const wf of BUILTIN_WORKFLOWS) {
      this.workflows.set(wf.id, wf);
    }
  }

  private loadUserWorkflows(): void {
    if (!existsSync(WORKFLOWS_PATH)) return;
    const raw = readFileSync(WORKFLOWS_PATH, 'utf-8');
    const userWorkflows = JSON.parse(raw) as WorkflowDefinition[];
    for (const wf of userWorkflows) {
      this.workflows.set(wf.id, wf);
    }
  }

  private saveUserWorkflows(): void {
    const userWorkflows = this.listAll().filter((w) => w.source === 'user-created');
    writeFileSync(WORKFLOWS_PATH, JSON.stringify(userWorkflows, null, 2));
  }

  get(id: string): WorkflowDefinition | undefined {
    return this.workflows.get(id);
  }

  listAll(): WorkflowDefinition[] {
    return Array.from(this.workflows.values());
  }

  listEnabled(): WorkflowDefinition[] {
    return this.listAll().filter((w) => w.enabled);
  }

  add(workflow: WorkflowDefinition): void {
    this.workflows.set(workflow.id, workflow);
    this.saveUserWorkflows();
  }

  update(id: string, updates: Partial<WorkflowDefinition>): WorkflowDefinition | undefined {
    const existing = this.workflows.get(id);
    if (!existing) return undefined;
    const updated = { ...existing, ...updates, id: existing.id };
    this.workflows.set(id, updated);
    if (updated.source === 'user-created') {
      this.saveUserWorkflows();
    }
    return updated;
  }

  remove(id: string): boolean {
    const wf = this.workflows.get(id);
    if (!wf || wf.source === 'builtin') return false;
    this.workflows.delete(id);
    this.saveUserWorkflows();
    return true;
  }

  toggleEnabled(id: string): WorkflowDefinition | undefined {
    const wf = this.workflows.get(id);
    if (!wf) return undefined;
    wf.enabled = !wf.enabled;
    if (wf.source === 'user-created') {
      this.saveUserWorkflows();
    }
    return wf;
  }
}

export function createWorkflowRegistry(): WorkflowRegistry {
  return new WorkflowRegistry();
}
