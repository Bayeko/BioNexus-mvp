import type { WorkflowDefinition } from './types.js';
import type { DecisionEngine } from '../engine/decision.js';
import type { PluginRegistry } from '../plugins/registry.js';
import type { Store } from '../store/index.js';
import type { SSEManager } from '../server/sse.js';
import type { EventBus } from '../engine/event-bus.js';
import { classifyProposalActions, getProposalRiskLevel } from '../engine/risk-classifier.js';

export interface WorkflowRunContext {
  decisionEngine: DecisionEngine;
  pluginRegistry: PluginRegistry;
  store: Store;
  sse: SSEManager;
  eventBus: EventBus;
}

export async function runWorkflow(
  workflow: WorkflowDefinition,
  ctx: WorkflowRunContext,
): Promise<string> {
  // Skip if a pending or executing proposal already exists for this workflow
  if (ctx.store.hasPendingProposal(workflow.id)) {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: `Skipping workflow "${workflow.name}": a pending proposal already exists`,
      workflowId: workflow.id,
    }));
    return '';
  }

  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    level: 'info',
    message: `Running workflow: ${workflow.name}`,
    workflowId: workflow.id,
  }));

  // Check that required connectors are enabled
  const missingConnectors = workflow.requiredConnectors.filter(
    (name) => !ctx.pluginRegistry.listEnabled().some((p) => p.name === name),
  );

  let contextNote = '';
  if (missingConnectors.length > 0) {
    contextNote = `\n\nNote: The following connectors are not enabled: ${missingConnectors.join(', ')}. Work with what is available and note any limitations.`;
  }

  const userContext = `Current time: ${new Date().toISOString()}\n\nWorkflow: ${workflow.name}\nDescription: ${workflow.description}${contextNote}\n\nExecute the following instruction:\n${workflow.instruction}`;

  const systemPrompt = `You are an AI orchestrator agent for BioNexus, a biotech startup building lab instrument integration software. You have access to tools from enabled connectors. Use the tools to gather information, then call propose_plan with your recommended actions. Be concise and actionable.`;

  // Run the decision engine
  const result = await ctx.decisionEngine.run(systemPrompt, userContext, ctx.pluginRegistry);

  // Classify risk levels on each action
  const overrides = ctx.store.listRiskOverrides();
  const classifiedActions = classifyProposalActions(result.actions, overrides);
  const proposalRisk = getProposalRiskLevel(classifiedActions);
  const autoApprove = proposalRisk !== 'red';

  // For yellow proposals, set a 5-minute undo deadline
  const undoDeadline = proposalRisk === 'yellow'
    ? new Date(Date.now() + 5 * 60 * 1000).toISOString()
    : undefined;

  // Store the proposal (auto-approved for green/yellow)
  const proposal = ctx.store.createProposal({
    workflowId: workflow.id,
    workflowName: workflow.name,
    summary: result.summary,
    actions: classifiedActions,
    reasoning: result.reasoning,
    riskLevel: proposalRisk,
    autoApproved: autoApprove,
    undoDeadline,
  });

  // Notify dashboard via SSE
  ctx.sse.broadcast('proposal:created', proposal);

  if (autoApprove) {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: `Auto-approved ${proposalRisk} proposal: ${proposal.summary}`,
      proposalId: proposal.id,
      riskLevel: proposalRisk,
    }));

    if (proposalRisk === 'green') {
      // Green: execute immediately
      ctx.eventBus.emit('proposal:approved', { proposalId: proposal.id });
    } else {
      // Yellow: delay execution by 5 minutes (undo window)
      setTimeout(() => {
        // Re-check status — user may have undone it
        const current = ctx.store.getProposal(proposal.id);
        if (current && current.status === 'approved') {
          ctx.eventBus.emit('proposal:approved', { proposalId: proposal.id });
        }
      }, 5 * 60 * 1000);
    }
  }

  return proposal.id;
}
