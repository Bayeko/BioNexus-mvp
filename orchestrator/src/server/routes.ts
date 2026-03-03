import { Router } from 'express';
import type { Store } from '../store/index.js';
import type { SSEManager } from './sse.js';
import type { PluginRegistry } from '../plugins/registry.js';
import type { WorkflowRegistry } from '../workflows/registry.js';
import type { EventBus } from '../engine/event-bus.js';
import type { WorkflowCreator } from '../engine/workflow-creator.js';
import { validateTransition } from '../engine/approval.js';

export interface RouteContext {
  store: Store;
  sse: SSEManager;
  pluginRegistry: PluginRegistry;
  workflowRegistry: WorkflowRegistry;
  eventBus: EventBus;
  workflowCreator: WorkflowCreator;
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

  return router;
}
