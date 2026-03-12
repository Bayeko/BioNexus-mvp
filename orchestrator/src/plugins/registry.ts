import type { ConnectorPlugin, ToolDefinition } from './types.js';
import type { Store } from '../store/index.js';

export class PluginRegistry {
  private plugins: Map<string, ConnectorPlugin> = new Map();

  constructor(private store: Store) {}

  register(plugin: ConnectorPlugin): void {
    this.plugins.set(plugin.name, plugin);
    // Initialize state in store if not present
    const existing = this.store.getConnectorState(plugin.name);
    if (!existing) {
      this.store.setConnectorState({
        name: plugin.name,
        enabled: false,
        configured: false,
      });
    }
  }

  get(name: string): ConnectorPlugin | undefined {
    return this.plugins.get(name);
  }

  listAll(): ConnectorPlugin[] {
    return Array.from(this.plugins.values());
  }

  listEnabled(): ConnectorPlugin[] {
    return this.listAll().filter((p) => {
      const state = this.store.getConnectorState(p.name);
      return state?.enabled;
    });
  }

  /** Collect tools from all enabled connectors, prefixed with connector name */
  getEnabledTools(): ToolDefinition[] {
    const tools: ToolDefinition[] = [];
    for (const plugin of this.listEnabled()) {
      for (const tool of plugin.tools) {
        tools.push({
          ...tool,
          name: `${plugin.name}__${tool.name}`,
        });
      }
    }
    return tools;
  }

  /** Route a tool call to the right connector */
  async executeTool(prefixedName: string, input: Record<string, unknown>): Promise<unknown> {
    const separatorIndex = prefixedName.indexOf('__');
    if (separatorIndex === -1) {
      throw new Error(`Invalid tool name format: ${prefixedName}`);
    }
    const connectorName = prefixedName.slice(0, separatorIndex);
    const toolName = prefixedName.slice(separatorIndex + 2);
    const plugin = this.plugins.get(connectorName);
    if (!plugin) {
      throw new Error(`Connector not found: ${connectorName}`);
    }
    return plugin.executeTool(toolName, input);
  }

  async enableConnector(name: string): Promise<void> {
    const plugin = this.plugins.get(name);
    if (!plugin) throw new Error(`Connector not found: ${name}`);

    await plugin.initialize({});
    const health = await plugin.healthCheck();

    this.store.setConnectorState({
      name,
      enabled: true,
      configured: health.ok,
      lastHealthCheck: { ...health, checkedAt: new Date().toISOString() },
    });
  }

  async disableConnector(name: string): Promise<void> {
    const plugin = this.plugins.get(name);
    if (!plugin) throw new Error(`Connector not found: ${name}`);

    await plugin.shutdown();

    const existing = this.store.getConnectorState(name);
    this.store.setConnectorState({
      name,
      enabled: false,
      configured: existing?.configured ?? false,
    });
  }

  async healthCheckAll(): Promise<void> {
    for (const plugin of this.listEnabled()) {
      const health = await plugin.healthCheck();
      const existing = this.store.getConnectorState(plugin.name);
      this.store.setConnectorState({
        name: plugin.name,
        enabled: existing?.enabled ?? false,
        configured: health.ok,
        lastHealthCheck: { ...health, checkedAt: new Date().toISOString() },
      });
    }
  }

  /** Initialize and enable all connectors that have valid credentials. */
  async autoEnableConfigured(): Promise<void> {
    for (const plugin of this.listAll()) {
      try {
        await plugin.initialize({});
        const health = await plugin.healthCheck();
        this.store.setConnectorState({
          name: plugin.name,
          enabled: health.ok,
          configured: health.ok,
          lastHealthCheck: { ...health, checkedAt: new Date().toISOString() },
        });
        if (health.ok) {
          console.log(`  ✓ ${plugin.displayName}: ${health.message ?? 'connected'}`);
        } else {
          console.log(`  ✗ ${plugin.displayName}: ${health.message ?? 'not configured'}`);
        }
      } catch (err) {
        this.store.setConnectorState({
          name: plugin.name,
          enabled: false,
          configured: false,
          lastHealthCheck: {
            ok: false,
            message: err instanceof Error ? err.message : String(err),
            checkedAt: new Date().toISOString(),
          },
        });
        console.log(`  ✗ ${plugin.displayName}: ${err instanceof Error ? err.message : String(err)}`);
      }
    }
  }
}

export function createPluginRegistry(store: Store): PluginRegistry {
  return new PluginRegistry(store);
}
