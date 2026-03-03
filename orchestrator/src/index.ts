import 'dotenv/config';
import express from 'express';
import { loadConfig } from './config.js';
import { setupMiddleware, errorHandler } from './server/middleware.js';
import { setupRoutes } from './server/routes.js';
import { createSSEManager } from './server/sse.js';
import { createStore } from './store/index.js';
import { createPluginRegistry } from './plugins/registry.js';
import { createEventBus } from './engine/event-bus.js';
import { createDecisionEngine } from './engine/decision.js';
import { createWorkflowCreator } from './engine/workflow-creator.js';
import { createWorkflowRegistry } from './workflows/registry.js';
import { createScheduler } from './engine/scheduler.js';
import { runWorkflow } from './workflows/runner.js';

// Connector plugins
import { GoogleCalendarPlugin } from './plugins/google-calendar/index.js';
import { GmailPlugin } from './plugins/gmail/index.js';
import { GoogleDrivePlugin } from './plugins/google-drive/index.js';
import { GitHubPlugin } from './plugins/github/index.js';

async function main(): Promise<void> {
  const config = loadConfig();
  const app = express();

  // Core infrastructure
  const store = createStore();
  const sse = createSSEManager();
  const eventBus = createEventBus();
  const decisionEngine = createDecisionEngine(config.anthropic.apiKey, config.anthropic.model);
  const workflowCreator = createWorkflowCreator(config.anthropic.apiKey, config.anthropic.model);

  // Plugin system — register all connectors
  const pluginRegistry = createPluginRegistry(store);
  pluginRegistry.register(new GoogleCalendarPlugin());
  pluginRegistry.register(new GmailPlugin());
  pluginRegistry.register(new GoogleDrivePlugin());
  pluginRegistry.register(new GitHubPlugin());

  // Workflow system
  const workflowRegistry = createWorkflowRegistry();

  // Express setup
  setupMiddleware(app);
  const routes = setupRoutes({
    store,
    sse,
    pluginRegistry,
    workflowRegistry,
    eventBus,
    workflowCreator,
  });
  app.use(routes);
  app.use(errorHandler);

  // Wire event bus: workflow triggers → run workflow → create proposal
  eventBus.on('workflow:trigger', async (event) => {
    const workflow = workflowRegistry.get(event.type);
    if (!workflow) {
      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'warn',
        message: `Unknown workflow triggered: ${event.type}`,
      }));
      return;
    }
    if (!workflow.enabled) {
      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'info',
        message: `Skipping disabled workflow: ${workflow.name}`,
      }));
      return;
    }
    try {
      await runWorkflow(workflow, { decisionEngine, pluginRegistry, store, sse });
    } catch (err) {
      console.error(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'error',
        message: `Workflow failed: ${workflow.name}`,
        error: String(err),
      }));
    }
  });

  // Start scheduler
  const scheduler = createScheduler(config.scheduler, eventBus, workflowRegistry);
  scheduler.start();

  // Start server
  app.listen(config.port, config.host, () => {
    console.log(`
╔══════════════════════════════════════════════╗
║       BioNexus Orchestrator v0.1.0           ║
╠══════════════════════════════════════════════╣
║  API:       http://${config.host}:${config.port}            ║
║  Dashboard: http://${config.host}:${config.port}/dashboard  ║
╚══════════════════════════════════════════════╝
    `);
    console.log(`Connectors: ${pluginRegistry.listAll().map((p) => p.name).join(', ')}`);
    console.log(`Workflows:  ${workflowRegistry.listAll().map((w) => w.name).join(', ')}`);
  });
}

main().catch((err) => {
  console.error('Failed to start orchestrator:', err);
  process.exit(1);
});
