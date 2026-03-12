import { Router } from 'express';
import type { Store } from '../store/index.js';
import type { SSEManager } from './sse.js';
import type { PluginRegistry } from '../plugins/registry.js';
import type { WorkflowRegistry } from '../workflows/registry.js';
import type { EventBus } from '../engine/event-bus.js';
import type { WorkflowCreator } from '../engine/workflow-creator.js';
import type { DecisionEngine } from '../engine/decision.js';
import type { RiskLevel } from '../store/types.js';
import { validateTransition } from '../engine/approval.js';

export interface RouteContext {
  store: Store;
  sse: SSEManager;
  pluginRegistry: PluginRegistry;
  workflowRegistry: WorkflowRegistry;
  eventBus: EventBus;
  workflowCreator: WorkflowCreator;
  decisionEngine: DecisionEngine;
}

export function setupRoutes(ctx: RouteContext): Router {
  const router = Router();

  // --- Health ---
  router.get('/api/health', (_req, res) => {
    res.json({
      status: 'ok',
      uptime: process.uptime(),
      connectors: ctx.pluginRegistry.listAll().length,
      workflows: ctx.workflowRegistry.listAll().length,
      sseClients: ctx.sse.clientCount,
    });
  });

  // --- SSE ---
  router.get('/api/sse', (req, res) => {
    ctx.sse.addClient(res);
    req.on('close', () => {
      // Client cleanup handled in SSEManager
    });
  });

  // --- Proposals ---
  router.get('/api/proposals', (req, res) => {
    const status = req.query.status as string | undefined;
    const proposals = ctx.store.listProposals(status as never);
    res.json(proposals);
  });

  router.get('/api/proposals/:id', (req, res) => {
    const proposal = ctx.store.getProposal(req.params.id);
    if (!proposal) {
      res.status(404).json({ error: 'Proposal not found' });
      return;
    }
    res.json(proposal);
  });

  router.post('/api/proposals/:id/approve', (req, res) => {
    const proposal = ctx.store.getProposal(req.params.id);
    if (!proposal) {
      res.status(404).json({ error: 'Proposal not found' });
      return;
    }
    try {
      validateTransition(proposal.status, 'approved');
    } catch (err) {
      res.status(400).json({ error: (err as Error).message });
      return;
    }
    const updated = ctx.store.updateProposalStatus(req.params.id, 'approved');
    ctx.sse.broadcast('proposal:updated', updated);
    ctx.eventBus.emit('proposal:approved', { proposalId: req.params.id });
    res.json(updated);
  });

  router.post('/api/proposals/:id/reject', (req, res) => {
    const proposal = ctx.store.getProposal(req.params.id);
    if (!proposal) {
      res.status(404).json({ error: 'Proposal not found' });
      return;
    }
    try {
      validateTransition(proposal.status, 'rejected');
    } catch (err) {
      res.status(400).json({ error: (err as Error).message });
      return;
    }
    const updated = ctx.store.updateProposalStatus(req.params.id, 'rejected', {
      error: req.body?.reason,
    });
    ctx.sse.broadcast('proposal:updated', updated);
    ctx.eventBus.emit('proposal:rejected', { proposalId: req.params.id });
    res.json(updated);
  });

  // --- Proposal Chat ---
  router.post('/api/proposals/:id/chat', async (req, res) => {
    const proposal = ctx.store.getProposal(req.params.id);
    if (!proposal) {
      res.status(404).json({ error: 'Proposal not found' });
      return;
    }

    const { message } = req.body;
    if (!message || typeof message !== 'string') {
      res.status(400).json({ error: 'Missing "message" in request body' });
      return;
    }

    // Store user message
    const userMsg = { role: 'user' as const, content: message, timestamp: new Date().toISOString() };
    ctx.store.appendChatMessage(req.params.id, userMsg);

    // Build proposal context for Claude
    const proposalContext = [
      `Workflow: ${proposal.workflowName}`,
      `Summary: ${proposal.summary}`,
      `Reasoning: ${proposal.reasoning}`,
      `Actions:\n${proposal.actions.map((a, i) => `  ${i + 1}. [${a.priority}] ${a.description}`).join('\n')}`,
      `Status: ${proposal.status}`,
      `Created: ${proposal.createdAt}`,
    ].join('\n');

    try {
      const reply = await ctx.decisionEngine.chat(
        proposalContext,
        proposal.chatHistory ?? [],
        message,
        ctx.pluginRegistry,
      );

      // Store assistant reply
      const assistantMsg = { role: 'assistant' as const, content: reply, timestamp: new Date().toISOString() };
      ctx.store.appendChatMessage(req.params.id, assistantMsg);

      // Re-fetch to get updated chatHistory
      const updated = ctx.store.getProposal(req.params.id)!;
      ctx.sse.broadcast('proposal:updated', updated);

      res.json({ reply, chatHistory: updated.chatHistory });
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
    }
  });

  router.post('/api/proposals/:id/revise', async (req, res) => {
    const proposal = ctx.store.getProposal(req.params.id);
    if (!proposal) {
      res.status(404).json({ error: 'Proposal not found' });
      return;
    }
    if (proposal.status !== 'pending_approval') {
      res.status(400).json({ error: 'Can only revise pending proposals' });
      return;
    }

    // Get the original workflow for context
    const workflow = ctx.workflowRegistry.get(proposal.workflowId);
    const workflowInstruction = workflow
      ? `Original Workflow Instruction:\n${workflow.instruction}`
      : '';
    const workflowContext = workflow
      ? `Workflow: ${workflow.name}\nDescription: ${workflow.description}`
      : `Workflow: ${proposal.workflowName}`;

    // Build FULL chat history with timestamps so Claude sees the entire discussion
    const chatHistory = (proposal.chatHistory ?? [])
      .map((m) => `[${m.timestamp}] ${m.role === 'user' ? 'USER' : 'ADVISOR'}: ${m.content}`)
      .join('\n\n');

    // Format previous actions including any toolCall details
    const previousActions = proposal.actions.map((a, i) => {
      let line = `  ${i + 1}. [${a.priority}] ${a.description}`;
      if (a.connector) line += `\n     Connector: ${a.connector}`;
      if (a.toolCall) line += `\n     Tool: ${a.toolCall.tool}\n     Input: ${JSON.stringify(a.toolCall.input)}`;
      return line;
    }).join('\n');

    const userContext = [
      `Current time: ${new Date().toISOString()}`,
      '',
      workflowContext,
      '',
      workflowInstruction,
      '',
      '═══ PREVIOUS PROPOSAL ═══',
      `Summary: ${proposal.summary}`,
      `Actions:\n${previousActions}`,
      `Reasoning: ${proposal.reasoning}`,
      '',
      chatHistory ? `═══ FULL DISCUSSION HISTORY ═══\n${chatHistory}` : '',
      '',
      '═══ YOUR TASK ═══',
      'Generate a REVISED proposal that addresses ALL of the user\'s feedback from the discussion above.',
      '',
      'CRITICAL RULES:',
      '1. Read EVERY message in the discussion history carefully.',
      '2. If the user provided specific values (folder IDs, file paths, URLs, names), you MUST use those EXACT values in your revised actions. Do NOT invent new IDs or create new folders when the user gave you existing ones.',
      '3. If the user said to remove an action, remove it. If they said to add one, add it. If they said to change a detail, change exactly that detail.',
      '4. Use the toolCall field on actions to specify exact tool parameters when the user provided specific values.',
      '5. Call propose_plan with the complete revised proposal.',
    ].filter(Boolean).join('\n');

    const systemPrompt = `You are an AI orchestrator revising a previously generated proposal based on user feedback. You have access to connector tools (Google Drive, GitHub, Gmail, Calendar) if you need to look up data. Your job is to produce a revised propose_plan that precisely incorporates every piece of feedback from the discussion history. Pay special attention to specific IDs, paths, or values the user mentioned — use them exactly as given.`;

    try {
      const result = await ctx.decisionEngine.run(systemPrompt, userContext, ctx.pluginRegistry);

      // Add a chat message noting the revision
      ctx.store.appendChatMessage(req.params.id, {
        role: 'assistant',
        content: `Proposal revised. New summary: ${result.summary}`,
        timestamp: new Date().toISOString(),
      });

      // Update the proposal in place
      const updated = ctx.store.updateProposal(req.params.id, {
        summary: result.summary,
        actions: result.actions,
        reasoning: result.reasoning,
      });

      ctx.sse.broadcast('proposal:updated', updated);
      res.json(updated);
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
    }
  });

  // --- Proposal Undo (yellow auto-approved) ---
  router.post('/api/proposals/:id/undo', (req, res) => {
    const proposal = ctx.store.getProposal(req.params.id);
    if (!proposal) {
      res.status(404).json({ error: 'Proposal not found' });
      return;
    }
    if (!proposal.autoApproved) {
      res.status(400).json({ error: 'Only auto-approved proposals can be undone' });
      return;
    }
    if (proposal.status !== 'approved') {
      res.status(400).json({ error: `Cannot undo proposal in "${proposal.status}" state` });
      return;
    }
    if (proposal.undoDeadline && new Date(proposal.undoDeadline) < new Date()) {
      res.status(400).json({ error: 'Undo window has expired' });
      return;
    }

    const updated = ctx.store.updateProposalStatus(req.params.id, 'rejected', {
      error: 'Undone by user within undo window',
    });
    ctx.sse.broadcast('proposal:updated', updated);
    res.json(updated);
  });

  // --- Workflows ---
  router.get('/api/workflows', (_req, res) => {
    res.json(ctx.workflowRegistry.listAll());
  });

  router.put('/api/workflows/:id', (req, res) => {
    const updated = ctx.workflowRegistry.update(req.params.id, req.body);
    if (!updated) {
      res.status(404).json({ error: 'Workflow not found' });
      return;
    }
    ctx.sse.broadcast('workflow:updated', updated);
    res.json(updated);
  });

  router.post('/api/workflows', (req, res) => {
    ctx.workflowRegistry.add(req.body);
    ctx.sse.broadcast('workflow:created', req.body);
    res.status(201).json(req.body);
  });

  router.delete('/api/workflows/:id', (req, res) => {
    const removed = ctx.workflowRegistry.remove(req.params.id);
    if (!removed) {
      res.status(400).json({ error: 'Cannot delete (not found or is builtin)' });
      return;
    }
    ctx.sse.broadcast('workflow:deleted', { id: req.params.id });
    res.json({ ok: true });
  });

  router.put('/api/workflows/:id/toggle', (req, res) => {
    const updated = ctx.workflowRegistry.toggleEnabled(req.params.id);
    if (!updated) {
      res.status(404).json({ error: 'Workflow not found' });
      return;
    }
    ctx.sse.broadcast('workflow:updated', updated);
    res.json(updated);
  });

  router.post('/api/workflows/:id/trigger', (req, res) => {
    const workflow = ctx.workflowRegistry.get(req.params.id);
    if (!workflow) {
      res.status(404).json({ error: 'Workflow not found' });
      return;
    }
    ctx.eventBus.emit('workflow:trigger', { type: workflow.id });
    res.json({ ok: true, message: `Triggered: ${workflow.name}` });
  });

  router.post('/api/workflows/create-from-prompt', async (req, res) => {
    const { prompt } = req.body;
    if (!prompt) {
      res.status(400).json({ error: 'Missing "prompt" in request body' });
      return;
    }
    try {
      const workflow = await ctx.workflowCreator.createFromPrompt(prompt, ctx.pluginRegistry);
      ctx.workflowRegistry.add(workflow);
      ctx.sse.broadcast('workflow:created', workflow);
      res.status(201).json(workflow);
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
    }
  });

  // --- Connectors ---
  router.get('/api/connectors', (_req, res) => {
    const connectors = ctx.pluginRegistry.listAll().map((plugin) => {
      const state = ctx.store.getConnectorState(plugin.name);
      return {
        name: plugin.name,
        displayName: plugin.displayName,
        description: plugin.description,
        toolCount: plugin.tools.length,
        enabled: state?.enabled ?? false,
        configured: state?.configured ?? false,
        lastHealthCheck: state?.lastHealthCheck,
      };
    });
    res.json(connectors);
  });

  router.put('/api/connectors/:name/enable', async (req, res) => {
    try {
      await ctx.pluginRegistry.enableConnector(req.params.name);
      const state = ctx.store.getConnectorState(req.params.name);
      ctx.sse.broadcast('connector:updated', state);
      res.json(state);
    } catch (err) {
      res.status(400).json({ error: (err as Error).message });
    }
  });

  router.put('/api/connectors/:name/disable', async (req, res) => {
    try {
      await ctx.pluginRegistry.disableConnector(req.params.name);
      const state = ctx.store.getConnectorState(req.params.name);
      ctx.sse.broadcast('connector:updated', state);
      res.json(state);
    } catch (err) {
      res.status(400).json({ error: (err as Error).message });
    }
  });

  // Re-read .env and re-initialize a connector without restarting the server
  router.post('/api/connectors/:name/reconnect', async (req, res) => {
    const plugin = ctx.pluginRegistry.get(req.params.name);
    if (!plugin) {
      res.status(404).json({ error: `Connector not found: ${req.params.name}` });
      return;
    }

    try {
      // Re-parse .env to pick up rotated tokens / changed credentials
      const dotenv = await import('dotenv');
      dotenv.config({ override: true });

      // Shutdown existing connection, then re-initialize with fresh env
      await plugin.shutdown();
      await plugin.initialize({});
      const health = await plugin.healthCheck();

      ctx.store.setConnectorState({
        name: plugin.name,
        enabled: health.ok,
        configured: health.ok,
        lastHealthCheck: { ...health, checkedAt: new Date().toISOString() },
      });

      const state = ctx.store.getConnectorState(plugin.name);
      ctx.sse.broadcast('connector:updated', state);

      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'info',
        message: `Reconnected connector: ${plugin.displayName} — ${health.message ?? (health.ok ? 'ok' : 'failed')}`,
      }));

      res.json({ ...state, healthCheck: health });
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
    }
  });

  // --- Risk Override Settings ---
  router.get('/api/settings/risk-overrides', (_req, res) => {
    res.json(ctx.store.listRiskOverrides());
  });

  router.post('/api/settings/risk-overrides', (req, res) => {
    const { pattern, riskLevel, description } = req.body;
    if (!pattern || typeof pattern !== 'string') {
      res.status(400).json({ error: 'Missing "pattern" string in request body' });
      return;
    }
    const validLevels: RiskLevel[] = ['green', 'yellow', 'red'];
    if (!validLevels.includes(riskLevel)) {
      res.status(400).json({ error: `"riskLevel" must be one of: ${validLevels.join(', ')}` });
      return;
    }
    const override = ctx.store.addRiskOverride({ pattern, riskLevel, description });
    res.status(201).json(override);
  });

  router.delete('/api/settings/risk-overrides/:id', (req, res) => {
    const removed = ctx.store.removeRiskOverride(req.params.id);
    if (!removed) {
      res.status(404).json({ error: 'Risk override not found' });
      return;
    }
    res.json({ ok: true });
  });

  return router;
}
