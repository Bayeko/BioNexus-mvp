import Anthropic from '@anthropic-ai/sdk';
import type { PluginRegistry } from '../plugins/registry.js';
import type { ToolDefinition } from '../plugins/types.js';
import type { ChatMessage } from '../store/types.js';

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
            connector: { type: 'string', description: 'Which connector this action uses (e.g. "google-drive", "github")' },
            toolCall: {
              type: 'object',
              properties: {
                tool: { type: 'string', description: 'The tool name to call (e.g. "google_drive_upload_file")' },
                input: {
                  type: 'object',
                  description: 'Exact input parameters for the tool call. For google-drive__create_document actions, include a "github_path" field (e.g. "docs/API_REFERENCE.md") instead of placeholder content — the executor will fetch the real file content from GitHub automatically.',
                },
              },
              required: ['tool', 'input'],
              description: 'Optional executable tool call. Use this to specify exact parameters — especially when the user provided specific values like folder IDs, file paths, etc.',
            },
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
          const input = block.input as {
            summary: string;
            actions: Array<{
              description: string;
              priority: 'high' | 'medium' | 'low';
              connector?: string;
              toolCall?: { tool: string; input: Record<string, unknown> };
            }>;
            reasoning: string;
          };
          proposedPlan = {
            summary: input.summary,
            actions: input.actions.map((a) => ({
              description: a.description,
              priority: a.priority,
              ...(a.connector && { connector: a.connector }),
              ...(a.toolCall && { toolCall: a.toolCall }),
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

  /**
   * Chat about a proposal. Claude acts as a strategic advisor with access to
   * connector tools for data lookups but no propose_plan tool.
   */
  async chat(
    proposalContext: string,
    chatHistory: ChatMessage[],
    userMessage: string,
    registry: PluginRegistry,
  ): Promise<string> {
    const connectorTools = registry.getEnabledTools().map(pluginToolToAnthropicTool);

    const systemPrompt = `You are a strategic advisor for BioNexus, a biotech startup. The user is reviewing a proposal generated by the orchestrator and wants to discuss it before deciding.

You have access to live connector tools (Calendar, Gmail, Drive, GitHub) to look up data if the user asks. Be concise, direct, and helpful. If the user wants changes to the proposal, acknowledge what should change — they can click "Revise" to regenerate it.

Current proposal context:
${proposalContext}`;

    // Build message history
    const messages: Anthropic.MessageParam[] = [];
    for (const msg of chatHistory) {
      messages.push({ role: msg.role, content: msg.content });
    }
    messages.push({ role: 'user', content: userMessage });

    // Agentic loop — Claude may call tools to fetch data
    for (let turn = 0; turn < 6; turn++) {
      const response = await this.client.messages.create({
        model: this.model,
        max_tokens: 2048,
        system: systemPrompt,
        tools: connectorTools.length > 0 ? connectorTools : undefined,
        messages,
      });

      const toolBlocks = response.content.filter(
        (b): b is Anthropic.ToolUseBlock => b.type === 'tool_use',
      );

      // No tool calls — extract text and return
      if (toolBlocks.length === 0 || response.stop_reason === 'end_turn') {
        const textBlock = response.content.find(
          (b): b is Anthropic.TextBlock => b.type === 'text',
        );
        return textBlock?.text ?? 'I couldn\'t formulate a response.';
      }

      // Execute tool calls
      const toolResults: Anthropic.ToolResultBlockParam[] = [];
      for (const block of toolBlocks) {
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

      messages.push({ role: 'assistant', content: response.content });
      messages.push({ role: 'user', content: toolResults });
    }

    return 'I ran out of turns processing your request. Could you rephrase?';
  }
}

export function createDecisionEngine(apiKey: string, model: string): DecisionEngine {
  return new DecisionEngine(apiKey, model);
}
