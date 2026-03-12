import type { Store } from '../store/index.js';
import type { PluginRegistry } from '../plugins/registry.js';
import type { SSEManager } from '../server/sse.js';

export interface ExecutorContext {
  store: Store;
  pluginRegistry: PluginRegistry;
  sse: SSEManager;
}

/**
 * If a create_document action includes a github_path, fetch the real file
 * content from GitHub and use it as the document body.
 */
async function resolveGitHubContent(
  tool: string,
  input: Record<string, unknown>,
  registry: PluginRegistry,
  log: (msg: string) => void,
): Promise<Record<string, unknown>> {
  // Only applies to Google Drive create_document with a github_path
  if (!tool.endsWith('__create_document') || !input.github_path) {
    return input;
  }

  const githubPath = input.github_path as string;
  log(`Fetching file content from GitHub: ${githubPath}`);

  const result = await registry.executeTool('github__get_file_content', { path: githubPath });
  const fileResult = result as { content?: string; error?: string };

  if (fileResult.error || !fileResult.content) {
    throw new Error(`Failed to fetch GitHub file "${githubPath}": ${fileResult.error ?? 'no content returned'}`);
  }

  log(`Fetched ${fileResult.content.length} chars from ${githubPath}`);

  // Replace content with real file content, drop the github_path field
  const { github_path: _, ...rest } = input;
  return { ...rest, content: fileResult.content };
}

/**
 * Execute an approved proposal: run each action's toolCall sequentially,
 * log results, and transition the proposal to completed or failed.
 */
export async function executeProposal(
  proposalId: string,
  ctx: ExecutorContext,
): Promise<void> {
  const proposal = ctx.store.getProposal(proposalId);
  if (!proposal || proposal.status !== 'approved') return;

  // Transition to executing
  ctx.store.updateProposalStatus(proposalId, 'executing');
  ctx.sse.broadcast('proposal:updated', ctx.store.getProposal(proposalId));
  ctx.store.appendExecutionLog(proposalId, 'Execution started');

  const actionsWithToolCalls = proposal.actions.filter((a) => a.toolCall);
  const skippedCount = proposal.actions.length - actionsWithToolCalls.length;

  if (skippedCount > 0) {
    ctx.store.appendExecutionLog(
      proposalId,
      `Skipping ${skippedCount} action(s) without executable toolCall`,
    );
  }

  const log = (msg: string) => ctx.store.appendExecutionLog(proposalId, msg);
  let failedAction: string | null = null;

  for (let i = 0; i < actionsWithToolCalls.length; i++) {
    const action = actionsWithToolCalls[i];
    const { tool } = action.toolCall!;
    const label = `[${i + 1}/${actionsWithToolCalls.length}] ${action.description}`;

    ctx.store.appendExecutionLog(proposalId, `Starting: ${label}`);
    ctx.sse.broadcast('proposal:updated', ctx.store.getProposal(proposalId));

    try {
      // Resolve GitHub content for create_document actions
      const resolvedInput = await resolveGitHubContent(
        tool,
        action.toolCall!.input,
        ctx.pluginRegistry,
        log,
      );

      const result = await ctx.pluginRegistry.executeTool(tool, resolvedInput);
      const resultSummary = typeof result === 'string'
        ? result.slice(0, 200)
        : JSON.stringify(result).slice(0, 200);
      ctx.store.appendExecutionLog(proposalId, `Completed: ${label} → ${resultSummary}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      ctx.store.appendExecutionLog(proposalId, `Failed: ${label} → ${errorMsg}`);
      failedAction = label;
      break;
    }
  }

  if (failedAction) {
    ctx.store.appendExecutionLog(proposalId, `Execution failed at: ${failedAction}`);
    ctx.store.updateProposalStatus(proposalId, 'failed', {
      error: `Action failed: ${failedAction}`,
    });
  } else {
    ctx.store.appendExecutionLog(proposalId, 'All actions completed successfully');
    ctx.store.updateProposalStatus(proposalId, 'completed');
  }

  ctx.sse.broadcast('proposal:updated', ctx.store.getProposal(proposalId));
}
