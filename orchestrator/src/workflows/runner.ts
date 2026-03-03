import type { WorkflowDefinition } from './types.js';
import type { DecisionEngine } from '../engine/decision.js';
import type { PluginRegistry } from '../plugins/registry.js';
import type { Store } from '../store/index.js';
import type { SSEManager } from '../server/sse.js';

export interface WorkflowRunContext {
  decisionEngine: DecisionEngine;
  pluginRegistry: PluginRegistry;
  store: Store;
  sse: SSEManager;
}

export async function runWorkflow(
  workflow: WorkflowDefinition,
  ctx: WorkflowRunContext,
): Promise<string> {
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

  // Store the proposal
  const proposal = ctx.store.createProposal({
    workflowId: workflow.id,
    workflowName: workflow.name,
    summary: result.summary,
    actions: result.actions,
    reasoning: result.reasoning,
  });

  // Notify dashboard via SSE
  ctx.sse.broadcast('proposal:created', proposal);

  return proposal.id;
}
