import Anthropic from '@anthropic-ai/sdk';
import { v4 as uuidv4 } from 'uuid';
import type { WorkflowDefinition } from '../workflows/types.js';
import type { PluginRegistry } from '../plugins/registry.js';

const SYSTEM_PROMPT = `You are a workflow configuration assistant for BioNexus Orchestrator.
Given a natural language description of a workflow, generate a structured WorkflowDefinition.

Available connectors: {connectors}

You must respond with a JSON object matching this schema:
{
  "name": "short descriptive name",
  "description": "what this workflow does",
  "trigger": {
    "type": "cron" | "event" | "manual",
    "cron": "cron expression (if type is cron)",
    "event": "event name (if type is event)"
  },
  "instruction": "detailed instruction for the AI agent that will execute this workflow",
  "requiredConnectors": ["list", "of", "connector", "names"]
}

Be precise with cron expressions. For event triggers, use format "connector:event_type".
The instruction field should be detailed enough for an AI to execute the workflow autonomously.`;

export class WorkflowCreator {
  private client: Anthropic;
  private model: string;

  constructor(apiKey: string, model: string) {
    this.client = new Anthropic({ apiKey });
    this.model = model;
  }

  async createFromPrompt(
    userPrompt: string,
    registry: PluginRegistry,
  ): Promise<WorkflowDefinition> {
    const connectorNames = registry.listAll().map((p) => p.name).join(', ');
    const system = SYSTEM_PROMPT.replace('{connectors}', connectorNames);

    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: 2048,
      system,
      messages: [{ role: 'user', content: userPrompt }],
    });

    const textBlock = response.content.find(
      (b): b is Anthropic.TextBlock => b.type === 'text',
    );

    if (!textBlock) {
      throw new Error('No response from Claude for workflow creation');
    }

    // Extract JSON from response (handle markdown code blocks)
    let jsonStr = textBlock.text;
    const jsonMatch = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
      jsonStr = jsonMatch[1];
    }

    const parsed = JSON.parse(jsonStr.trim()) as Omit<WorkflowDefinition, 'id' | 'enabled' | 'source'>;

    return {
      id: uuidv4(),
      enabled: true,
      source: 'user-created',
      ...parsed,
    };
  }
}

export function createWorkflowCreator(apiKey: string, model: string): WorkflowCreator {
  return new WorkflowCreator(apiKey, model);
}
