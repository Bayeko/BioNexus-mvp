export interface ToolDefinition {
  name: string;
  description: string;
  input_schema: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
}

export interface ConnectorPlugin {
  /** Unique identifier, e.g. 'google-calendar' */
  name: string;
  /** Human-readable name, e.g. 'Google Calendar' */
  displayName: string;
  /** Short description of what this connector does */
  description: string;

  /** Tools this connector exposes to Claude */
  tools: ToolDefinition[];

  /** Execute a tool call from Claude. Returns the result data. */
  executeTool(name: string, input: Record<string, unknown>): Promise<unknown>;

  /** Check if the connector is configured and reachable */
  healthCheck(): Promise<{ ok: boolean; message?: string }>;

  /** Initialize the connector with credentials/config */
  initialize(config: Record<string, string>): Promise<void>;

  /** Graceful shutdown */
  shutdown(): Promise<void>;
}
