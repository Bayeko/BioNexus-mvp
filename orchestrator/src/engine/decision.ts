import Anthropic from '@anthropic-ai/sdk';
import type { PluginRegistry } from '../plugins/registry.js';
import type { ToolDefinition } from '../plugins/types.js';

export interface DecisionResult {
  summary: string;
  actions: Array<{
    description: string;
    priority: 'high' | 'medium' | 'low';
    connector?: string;
    toolCall?: { tool: string; input: Record<string, unknown> };
  }>;
  reasoning: string;
}

const PROPOSE_PLAN_TOOL: Anthropic.Tool = {
  name: 'propose_plan',
  description: 'Submit your proposed plan of actions for human approval. Call this when you have gathered enough context and are ready to present a plan.',
  input_schema: {
    type: 'object' as const,
    properties: {
      summary: { type: 'string', description: 'One-line summary of the proposed plan' },
      actions: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            description: { type: 'string', description: 'What this action does' },
            priority: { type: 'string', enum: ['high', 'medium', 'low'] },
          },
          required: ['description', 'priority'],
        },
        description: 'Ordered list of proposed actions',
      },
      reasoning: { type: 'string', description: 'Why you recommend this plan' },
    },
    required: ['summary', 'actions', 'reasoning'],
  },
};

function pluginToolToAnthropicTool(tool: ToolDefinition): Anthropic.Tool {
  return {
    name: tool.name,
    description: tool.description,
    input_schema: tool.input_schema as Anthropic.Tool.InputSchema,
  };
}

export class DecisionEngine {
  private client: Anthropic;
  private model: string;

  constructor(apiKey: string, model: string) {
    this.client = new Anthropic({ apiKey });
    this.model = model;
  }

  async run(
    systemPrompt: string,
    userContext: string,
    registry: PluginRegistry,
  ): Promise<DecisionResult> {
    const connectorTools = registry.getEnabledTools().map(pluginToolToAnthropicTool);
    const allTools: Anthropic.Tool[] = [...connectorTools, PROPOSE_PLAN_TOOL];

    const messages: Anthropic.MessageParam[] = [
      { role: 'user', content: userContext },
    ];

    let proposedPlan: DecisionResult | null = null;

    // Agentic loop: let Claude call tools until it proposes a plan
    for (let turn = 0; turn < 10; turn++) {
      const response = await this.client.messages.create({
        model: this.model,
        max_tokens: 4096,
        system: systemPrompt,
        tools: allTools,
        messages,
      });

      // Check if Claude proposed a plan via tool_use
      const toolBlocks = response.content.filter(
        (b): b is Anthropic.ToolUseBlock => b.type === 'tool_use',
      );

      if (toolBlocks.length === 0 || response.stop_reason === 'end_turn') {
        // Claude finished without proposing — extract from text
        const textBlock = response.content.find(
          (b): b is Anthropic.TextBlock => b.type === 'text',
        );
        if (textBlock) {
          proposedPlan = {
            summary: textBlock.text.slice(0, 200),
            actions: [{ description: textBlock.text, priority: 'medium' }],
            reasoning: 'Claude provided a text response without using propose_plan tool.',
          };
        }
        break;
      }

      // Process tool calls
      const toolResults: Anthropic.ToolResultBlockParam[] = [];

      for (const block of toolBlocks) {
        if (block.name === 'propose_plan') {
          // This is the final output
          const input = block.input as { summary: string; actions: Array<{ description: string; priority: 'high' | 'medium' | 'low' }>; reasoning: string };
          proposedPlan = {
            summary: input.summary,
            actions: input.actions.map((a) => ({
              description: a.description,
              priority: a.priority,
            })),
            reasoning: input.reasoning,
          };
          toolResults.push({
            type: 'tool_result',
            tool_use_id: block.id,
            content: JSON.stringify({ status: 'Plan submitted for human approval.' }),
          });
        } else {
          // Execute connector tool
          try {
            const result = await registry.executeTool(block.name, block.input as Record<string, unknown>);
            toolResults.push({
              type: 'tool_result',
              tool_use_id: block.id,
              content: JSON.stringify(result),
            });
          } catch (err) {
            toolResults.push({
              type: 'tool_result',
              tool_use_id: block.id,
              content: JSON.stringify({ error: String(err) }),
              is_error: true,
            });
          }
        }
      }

      // If we got a plan, we're done
      if (proposedPlan) break;

      // Continue the conversation
      messages.push({ role: 'assistant', content: response.content });
      messages.push({ role: 'user', content: toolResults });
    }

    return proposedPlan ?? {
      summary: 'No plan could be generated',
      actions: [],
      reasoning: 'Claude did not produce a plan within the turn limit.',
    };
  }
}

export function createDecisionEngine(apiKey: string, model: string): DecisionEngine {
  return new DecisionEngine(apiKey, model);
}
