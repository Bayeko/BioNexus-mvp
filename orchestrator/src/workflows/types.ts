export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: {
    type: 'cron' | 'event' | 'manual';
    cron?: string;
    event?: string;
  };
  /** Natural language instruction for Claude describing what to do */
  instruction: string;
  /** Which connectors this workflow needs */
  requiredConnectors: string[];
  /** Built-in or created by user via natural language */
  source: 'builtin' | 'user-created';
}
