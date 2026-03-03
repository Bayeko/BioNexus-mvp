# Architecture Decision Record: Tier 2 Multi-Agent Orchestrator
## BioNexus Platform — ADR-002

---

**Document ID:** BNX-ADR-002
**Version:** 1.0
**Status:** Proposed
**Date:** 2026-03-03
**Classification:** Architecture — Internal Engineering

---

## Document Control

### Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2026-03-03 | BioNexus Engineering | Initial proposal for Tier 2 Multi-Agent Orchestrator |

### Related Documents

| Document ID | Title |
|-------------|-------|
| BNX-ADR-001 | Architecture Decision Record: AI Extraction Service |
| BNX-HW-001 | BioNexus Box — Hardware Gateway Architecture |
| BNX-SEC-001 | Security Architecture |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Architecture Overview](#3-architecture-overview)
4. [Core Concepts](#4-core-concepts)
5. [Technology Stack](#5-technology-stack)
6. [Connector Plugins](#6-connector-plugins)
7. [Workflow Definitions](#7-workflow-definitions)
8. [Claude Integration](#8-claude-integration)
9. [Dashboard Architecture](#9-dashboard-architecture)
10. [Scheduling & Events](#10-scheduling--events)
11. [Security & Credentials](#11-security--credentials)
12. [API Reference](#12-api-reference)
13. [Future Extensibility](#13-future-extensibility)

---

## 1. Executive Summary

The Tier 2 Multi-Agent Orchestrator is a locally-hosted Node.js server that uses Claude as its decision engine to coordinate automated workflows across Google Calendar, Gmail, Google Drive, and GitHub. It employs a plugin-based connector system where each external API is an independent, self-registering module. A React dashboard serves as the single command center for the BioNexus engineering team, providing real-time visibility into scheduled workflows, pending proposals, and connector health. Every action the orchestrator proposes — sending an email, creating a document, commenting on a pull request — requires explicit human approval before execution, enforcing a strict human-in-the-loop policy that prevents unintended side effects while still eliminating the manual effort of gathering context, drafting artifacts, and switching between tools.

---

## 2. Problem Statement

The BioNexus engineering and operations team coordinates work across a fragmented set of tools: Google Calendar for meetings and scheduling, Gmail for partner and customer communication, Google Drive for regulatory documents and specifications, and GitHub for code, issues, and pull requests. On a typical day, a team member context-switches between these platforms dozens of times — checking the morning calendar, scanning unread emails for action items, reviewing overnight pull requests, and cross-referencing Drive documents before meetings.

This fragmentation creates three concrete problems:

1. **Context assembly is manual and repetitive.** Preparing for a meeting with GMP4U requires opening Calendar for the agenda, Drive for the latest compliance document, Gmail for the last thread with Johannes, and GitHub for the current sprint status. This takes 10-15 minutes per meeting and produces no reusable artifact.

2. **Cross-tool actions require human glue.** When a new architecture document lands in GitHub, it should be mirrored or linked in Drive. When a weekly review is due, commit history, calendar utilization, and email response times should be aggregated into a scorecard. These workflows are predictable but not automated.

3. **No unified operational view exists.** There is no single place to see today's calendar alongside unread emails, open PRs, and pending document reviews. Each tool has its own notification system, and important items fall through the cracks.

The Tier 2 Orchestrator solves these problems by running scheduled and event-driven workflows that use Claude to read from connected tools, synthesize information, and propose actions — all surfaced through a single dashboard where the team can approve, reject, or modify proposals before they execute.

---

## 3. Architecture Overview

### 3.1 System Context Diagram

```
+---------------------+
|   BioNexus Team     |
|   (Human Operator)  |
+---------+-----------+
          |
          | Browser (localhost:5173)
          |
+---------v-----------+         SSE (real-time updates)
|                     +----------------------------+
|   React Dashboard   |                            |
|   (Vite SPA)        |         REST API           |
+---------+-----------+----------------------------+
          |                                        |
          | HTTP (localhost:3000)                   |
          |                                        |
+---------v----------------------------------------v--+
|                                                     |
|              Express Server (Node.js)               |
|                                                     |
|  +-------------+  +-------------+  +--------------+ |
|  | Scheduler   |  | Workflow    |  | Proposal     | |
|  | (node-cron) |  | Engine      |  | Manager      | |
|  +------+------+  +------+------+  +------+-------+ |
|         |                |                |          |
|         +--------+-------+--------+-------+          |
|                  |                |                   |
|          +-------v-------+  +----v-----+             |
|          | Claude SDK    |  | SSE Bus  |             |
|          | (Decision     |  | (Event   |             |
|          |  Engine)      |  |  Stream) |             |
|          +-------+-------+  +----------+             |
|                  |                                   |
|          +-------v----------------------------------+|
|          |         Plugin System                    ||
|          |                                          ||
|          |  +----------+ +-------+ +-------+ +----+||
|          |  | Calendar | | Gmail | | Drive | | GH |||
|          |  +----+-----+ +---+---+ +---+---+ +-+--+||
|          +-------|-----------|----------|-------|----|+
+------------------|-----------|----------|-------|----|
                   |           |          |       |
                   v           v          v       v
              Google Cal   Gmail API   Drive   GitHub
              API          API         API     API
```

### 3.2 Component Diagram

```
+------------------------------------------------------------------+
|                        Express Server                            |
|                                                                  |
|  +-----------------+     +------------------+                    |
|  | REST Router     |     | SSE Manager      |                   |
|  | /api/proposals  |     | /api/events      |                   |
|  | /api/workflows  |     | push updates to  |                   |
|  | /api/connectors |     | connected clients|                   |
|  +--------+--------+     +--------+---------+                   |
|           |                       ^                              |
|           v                       |                              |
|  +--------+--------+     +-------+---------+                    |
|  | Workflow Engine  +---->+ Proposal Manager|                   |
|  | - load defs      |     | - create        |                   |
|  | - run workflow    |     | - approve/reject|                   |
|  | - collect results |     | - execute       |                   |
|  +--------+---------+     | - state machine |                   |
|           |               +-----------------+                    |
|           v                                                      |
|  +--------+---------+                                            |
|  | Claude SDK Client |                                           |
|  | - system prompt   |                                           |
|  | - tool defs       |                                           |
|  | - agentic loop    |                                           |
|  +--------+----------+                                           |
|           |                                                      |
|           v                                                      |
|  +--------+--------------------------------------------------+   |
|  | Connector Plugin Registry                                 |   |
|  |                                                           |   |
|  |  ConnectorPlugin interface:                               |   |
|  |    name, getTools(), executeTool(), getStatus()           |   |
|  |                                                           |   |
|  |  Registered Plugins:                                      |   |
|  |    [GoogleCalendar] [Gmail] [GoogleDrive] [GitHub]        |   |
|  +-----------------------------------------------------------+   |
+------------------------------------------------------------------+
```

### 3.3 Data Flow

The core data flow for every workflow execution follows this sequence:

```
Trigger (cron / event / manual)
        |
        v
Scheduler invokes Workflow Engine with WorkflowDefinition
        |
        v
Workflow Engine loads instruction + required connectors
        |
        v
Workflow Engine calls Claude SDK with:
  - System prompt (from workflow instruction)
  - Tool definitions (from enabled connectors)
        |
        v
Claude enters agentic tool_use loop:
  Claude requests tool call --> Orchestrator executes via connector --> Result returned to Claude
  (repeats until Claude has enough context)
        |
        v
Claude returns structured proposal (actions to take)
        |
        v
Proposal Manager creates proposal record (state: pending_approval)
        |
        v
SSE Manager pushes proposal to connected dashboard clients
        |
        v
Human reviews proposal in dashboard
        |
        +---> Approved --> Proposal Manager executes actions via connectors
        |                       |
        |                       +--> completed / failed
        |
        +---> Rejected --> Proposal archived, no action taken
```

---

## 4. Core Concepts

### 4.1 Agent Tiers

The orchestrator architecture defines three tiers of agent capability, of which this document specifies the second:

| Tier | Role | Scope | Implementation |
|------|------|-------|----------------|
| **Tier 1** | Individual tool connectors | Single API interactions — read calendar events, list PRs, search emails | Connector plugins (this system's building blocks) |
| **Tier 2** | Orchestrator (this document) | Multi-tool coordination — combine calendar + email + code context to produce actionable proposals | Node.js server with Claude as decision engine |
| **Tier 3** | Strategic layer (future) | Long-range planning — prioritize features across sprints, suggest resource allocation, track OKR progress | Not yet specified |

Tier 1 connectors are stateless and single-purpose. They expose tool definitions and execute tool calls. They have no decision-making capability.

Tier 2 is where intelligence lives. The orchestrator uses Claude to interpret context gathered from Tier 1 connectors, reason about what actions are appropriate, and formulate proposals. It does not act autonomously — every proposed action passes through human approval.

Tier 3, when implemented, would consume Tier 2 outputs (completed workflows, historical proposals, accumulated data) to make strategic recommendations over longer time horizons.

### 4.2 Connector Plugin System

Each external API is wrapped in an independent plugin that implements the `ConnectorPlugin` interface. Plugins are self-contained: they manage their own authentication, define their own tools, and handle their own error recovery. The orchestrator discovers plugins at startup and registers their tools with the Claude SDK.

```typescript
interface ConnectorPlugin {
  /** Unique identifier for this connector */
  name: string;

  /** Human-readable description */
  description: string;

  /**
   * Returns the list of tools this connector provides.
   * Each tool follows the Anthropic tool definition schema:
   * { name, description, input_schema }
   */
  getTools(): ToolDefinition[];

  /**
   * Executes a tool call by name with the given input.
   * Called by the orchestrator during Claude's agentic loop.
   */
  executeTool(toolName: string, input: Record<string, unknown>): Promise<unknown>;

  /**
   * Returns the current health/connection status of this connector.
   * Used by the dashboard to display connector state.
   */
  getStatus(): ConnectorStatus;
}

interface ConnectorStatus {
  connected: boolean;
  lastChecked: Date;
  error?: string;
}

interface ToolDefinition {
  name: string;
  description: string;
  input_schema: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
}
```

When the orchestrator starts, it iterates over all registered plugins, calls `getTools()` on each, and aggregates the tool definitions. When a workflow runs, only the tools from connectors listed in the workflow's `requiredConnectors` array are passed to Claude, limiting the tool surface to what is relevant.

### 4.3 Workflow Definitions

Workflows are data-driven, not hardcoded. Each workflow is defined by a `WorkflowDefinition` object that specifies when it should trigger, what instruction to give Claude, and which connectors it needs. This design means new workflows can be added without writing code — including by having Claude itself generate definitions from natural language descriptions.

```typescript
interface WorkflowDefinition {
  /** Unique identifier */
  id: string;

  /** Human-readable name shown in the dashboard */
  name: string;

  /** Optional longer description */
  description?: string;

  /** Trigger configuration */
  trigger: {
    type: "cron" | "event" | "manual";
    /** Cron expression (if type is "cron") */
    schedule?: string;
    /** Event name to listen for (if type is "event") */
    eventName?: string;
  };

  /** The instruction given to Claude as its system prompt for this workflow.
   *  This is the core of the workflow — it tells Claude what to do,
   *  what to look for, and how to format its proposal. */
  instruction: string;

  /** Which connectors this workflow needs access to.
   *  Only tools from these connectors are provided to Claude. */
  requiredConnectors: string[];

  /** Whether this workflow is currently active */
  enabled: boolean;
}
```

The `instruction` field is a plain-English prompt. For example, the Morning Kick-off workflow's instruction reads: "You are a daily planning assistant. Check today's calendar for meetings, scan unread emails for anything urgent, and review overnight GitHub activity. Produce a structured daily plan with a prioritized task list, meeting preparation notes, and flagged items requiring attention."

This prompt-driven design means the team can iterate on workflow behavior by editing a string rather than modifying control flow logic.

### 4.4 Human-in-the-Loop

Every action the orchestrator proposes must be explicitly approved by a human before execution. There is no auto-execute mode. This is a deliberate design constraint, not a temporary limitation.

The proposal lifecycle follows a state machine:

```
                    +-------------------+
                    |  pending_approval |
                    +--------+----------+
                             |
                  +----------+----------+
                  |                     |
          +-------v------+     +-------v-------+
          |   approved   |     |   rejected    |
          +-------+------+     +---------------+
                  |
          +-------v------+
          |  executing   |
          +-------+------+
                  |
         +--------+--------+
         |                  |
  +------v------+   +------v------+
  |  completed  |   |   failed    |
  +-------------+   +-------------+
```

```typescript
interface Proposal {
  id: string;
  workflowId: string;
  workflowName: string;
  status: "pending_approval" | "approved" | "rejected" | "executing" | "completed" | "failed";
  summary: string;
  actions: ProposedAction[];
  reasoning: string;
  createdAt: Date;
  resolvedAt?: Date;
  error?: string;
}

interface ProposedAction {
  connector: string;
  tool: string;
  parameters: Record<string, unknown>;
  description: string;
}
```

When Claude completes its agentic loop, it returns a structured output containing a summary, a list of proposed actions, and its reasoning. The Proposal Manager wraps this in a `Proposal` record, sets the status to `pending_approval`, and emits it via SSE to the dashboard. The human operator can inspect the reasoning, review each proposed action, and approve or reject the entire proposal.

On approval, the Proposal Manager iterates over the `actions` array and calls the appropriate connector's `executeTool()` method for each one. If any action fails, the proposal transitions to `failed` with the error recorded.

---

## 5. Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Server runtime | Node.js 20+ | Event-driven, non-blocking I/O suitable for concurrent API calls and SSE streams |
| Language | TypeScript 5.x | Type safety across plugin interfaces, workflow definitions, and API contracts |
| HTTP framework | Express 4.x | REST API endpoints and SSE streaming |
| AI decision engine | `@anthropic-ai/sdk` | Claude Sonnet integration for workflow reasoning and tool use |
| Google APIs | `googleapis` | OAuth2 client and service wrappers for Calendar, Gmail, and Drive |
| GitHub API | `@octokit/rest` | Authenticated REST client for GitHub repositories, PRs, commits, and files |
| Scheduling | `node-cron` | Cron-based scheduling for time-triggered workflows |
| Dashboard framework | React 18 + Vite | Single-page application for the operator dashboard |
| Dashboard language | TypeScript | Shared type definitions between server and client |
| Real-time transport | Server-Sent Events (SSE) | Push-based updates from server to dashboard without WebSocket complexity |
| Process management | `tsx` (dev) / `node` (prod) | TypeScript execution in development, compiled JS in production |

Claude Sonnet is selected as the decision model rather than Opus because the orchestrator's tasks — summarizing calendar events, categorizing emails, generating action plans — are well within Sonnet's capability envelope. The lower latency and cost per token allow the system to run multiple workflows per day without significant API expense.

---

## 6. Connector Plugins

### 6.1 Google Calendar Connector

**Purpose:** Provides read access to the operator's Google Calendar for meeting context, scheduling awareness, and time-based workflow triggers.

**Authentication:** Google OAuth2 with offline access (refresh token stored in `.env`).

**Tools:**

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `list_events` | Returns calendar events within a specified date range. Defaults to today. | `startDate?: string`, `endDate?: string`, `maxResults?: number` |
| `get_event` | Retrieves full details for a single event by ID, including attendees, description, and attachments. | `eventId: string` |
| `get_upcoming_meetings` | Returns the next N meetings from the current moment. Convenience wrapper around `list_events` with pre-set time window. | `count?: number` (default: 5) |

**Use Cases:** Morning kick-off (what meetings are today), meeting prep (what is the next meeting about and who is attending), weekly review (how many meetings this week, total meeting hours).

### 6.2 Gmail Connector

**Purpose:** Provides read access to Gmail for identifying action items, extracting context from email threads, and surfacing urgent messages.

**Authentication:** Google OAuth2 with Gmail readonly scope. Same OAuth2 client as the Calendar connector.

**Tools:**

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `search_messages` | Searches Gmail using Gmail query syntax (e.g., `from:johannes is:unread`). Returns message summaries. | `query: string`, `maxResults?: number` |
| `get_message` | Retrieves the full content of a single email by ID, including body text and attachment metadata. | `messageId: string` |
| `list_unread` | Returns all unread messages in the inbox, ordered by date descending. | `maxResults?: number` (default: 20) |

**Use Cases:** Morning kick-off (any urgent unread emails), meeting prep (last email thread with each meeting attendee), cross-agent sync (emails referencing GitHub issues or Drive documents).

### 6.3 Google Drive Connector

**Purpose:** Provides read and write access to Google Drive for document retrieval, content extraction, and document creation.

**Authentication:** Google OAuth2 with Drive file scope. Same OAuth2 client as Calendar and Gmail connectors.

**Tools:**

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `list_files` | Lists files in a specified Drive folder or the root. Supports filtering by MIME type. | `folderId?: string`, `mimeType?: string`, `maxResults?: number` |
| `get_file_content` | Retrieves the text content of a Google Doc or the metadata of a binary file. | `fileId: string` |
| `create_document` | Creates a new Google Doc with the specified title and content. Returns the document URL. | `title: string`, `content: string`, `folderId?: string` |
| `search_files` | Full-text search across Drive files. Uses Drive's native query capabilities. | `query: string`, `maxResults?: number` |

**Use Cases:** Meeting prep (find the most recent spec or compliance doc related to a meeting topic), cross-agent sync (mirror GitHub architecture docs as Drive documents), weekly review (list documents created or modified this week).

### 6.4 GitHub Connector

**Purpose:** Provides read access to the BioNexus GitHub repository for code activity awareness — recent commits, open pull requests, and newly created files.

**Authentication:** GitHub personal access token stored in `.env`. Uses `@octokit/rest` for API calls.

**Tools:**

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `list_commits` | Returns recent commits on a specified branch. Defaults to `main`. | `branch?: string`, `since?: string`, `maxResults?: number` |
| `list_prs` | Lists open pull requests with title, author, labels, and review status. | `state?: string` (default: "open"), `maxResults?: number` |
| `list_recently_created_files` | Identifies files created in the last N days by analyzing commit diffs. Useful for detecting new documentation or architecture artifacts. | `days?: number` (default: 7), `branch?: string` |

**Use Cases:** Morning kick-off (overnight commits and new PRs), cross-agent sync (new docs in `docs/` that should be linked in Drive), weekly review (total commits, PR merge rate, contributors).

### 6.5 Adding New Connectors

To add a new connector — for example, a Slack integration — create a new TypeScript file that implements the `ConnectorPlugin` interface:

```typescript
// src/connectors/slack.ts

import { ConnectorPlugin, ConnectorStatus, ToolDefinition } from "../types";
import { WebClient } from "@slack/web-api";

export class SlackConnector implements ConnectorPlugin {
  name = "slack";
  description = "Read and send messages in Slack channels";

  private client: WebClient;

  constructor() {
    this.client = new WebClient(process.env.SLACK_BOT_TOKEN);
  }

  getTools(): ToolDefinition[] {
    return [
      {
        name: "slack_list_channels",
        description: "List Slack channels the bot has access to",
        input_schema: {
          type: "object",
          properties: {
            limit: { type: "number", description: "Max channels to return" },
          },
        },
      },
      {
        name: "slack_read_messages",
        description: "Read recent messages from a Slack channel",
        input_schema: {
          type: "object",
          properties: {
            channel: { type: "string", description: "Channel ID" },
            limit: { type: "number", description: "Max messages to return" },
          },
          required: ["channel"],
        },
      },
    ];
  }

  async executeTool(toolName: string, input: Record<string, unknown>): Promise<unknown> {
    switch (toolName) {
      case "slack_list_channels":
        return this.client.conversations.list({ limit: (input.limit as number) ?? 20 });
      case "slack_read_messages":
        return this.client.conversations.history({
          channel: input.channel as string,
          limit: (input.limit as number) ?? 10,
        });
      default:
        throw new Error(`Unknown tool: ${toolName}`);
    }
  }

  getStatus(): ConnectorStatus {
    return { connected: !!process.env.SLACK_BOT_TOKEN, lastChecked: new Date() };
  }
}
```

Then register it in the connector registry at startup:

```typescript
// src/connectors/index.ts
import { SlackConnector } from "./slack";

registry.register(new SlackConnector());
```

No other code changes are required. The orchestrator will automatically discover the new connector's tools and make them available to workflows that list `"slack"` in their `requiredConnectors` array.

---

## 7. Workflow Definitions

### 7.1 Morning Kick-off

**Trigger:** Cron — `0 8 * * 1-5` (08:00 Monday through Friday)

**Required Connectors:** `google-calendar`, `gmail`, `github`

**Instruction:**
> You are a daily planning assistant for the BioNexus engineering team. Perform these steps:
> 1. List today's calendar events to understand the day's meetings and commitments.
> 2. Check for unread emails, especially from GMP4U (Johannes), customers, or with urgent subject lines.
> 3. List overnight GitHub activity — new commits on main, open PRs needing review, and any newly created files.
> 4. Synthesize a daily plan with: (a) prioritized task list, (b) meeting preparation notes for each meeting, (c) flagged emails requiring response, (d) GitHub items needing attention.
> Format the output as a structured summary suitable for display in a dashboard card.

**Output:** A proposal containing the daily plan as structured text. No actions to execute — this workflow is informational. The proposal is auto-displayed in the dashboard's Activity Feed.

### 7.2 Cross-Agent Sync

**Trigger:** Cron — `0 */4 * * 1-5` (every 4 hours during weekdays)

**Required Connectors:** `github`, `google-drive`

**Instruction:**
> You are a documentation sync assistant. Check GitHub for any new files created in the `docs/` directory since the last sync. For each new document, check whether a corresponding file exists in Google Drive's BioNexus Documentation folder. If a GitHub doc has no Drive counterpart, propose creating a Google Doc with the same content. Include the GitHub source URL in the Drive document's header.

**Output:** A proposal listing zero or more `create_document` actions on the Google Drive connector. Each action includes the document title, content (pulled from GitHub), and target Drive folder. The operator approves to sync or rejects if the document is not ready for Drive distribution.

### 7.3 Meeting Prep

**Trigger:** Event-driven — fires 30 minutes before each calendar event that has at least one external attendee.

**Required Connectors:** `google-calendar`, `gmail`, `google-drive`

**Instruction:**
> You are a meeting preparation assistant. For the upcoming meeting:
> 1. Retrieve the full event details (attendees, agenda, description).
> 2. Search Gmail for the 5 most recent email threads involving any of the meeting's attendees.
> 3. Search Google Drive for documents related to the meeting topic (use keywords from the meeting title and description).
> 4. Produce a meeting prep brief containing: (a) meeting basics (time, attendees, agenda), (b) key points from recent email exchanges with attendees, (c) relevant documents with links, (d) suggested talking points based on the gathered context.

**Output:** A proposal containing the meeting prep brief as structured text displayed in the dashboard. Optionally proposes creating a Google Doc with the prep notes if the meeting has more than 3 attendees (indicating a more formal meeting requiring shared preparation).

### 7.4 Weekly Review

**Trigger:** Cron — `0 17 * * 5` (17:00 every Friday)

**Required Connectors:** `google-calendar`, `gmail`, `github`

**Instruction:**
> You are a weekly review analyst. Generate a scorecard for the past week (Monday through today):
> 1. Calendar: total meetings, total meeting hours, meetings by category (internal/external/partner).
> 2. GitHub: total commits on main, PRs opened, PRs merged, PRs still open, new files in docs/ or architecture areas.
> 3. Email: total emails received, emails sent, threads with GMP4U or customers, average response time if determinable.
> 4. Produce a weekly scorecard with these metrics, a brief narrative summary of the week's key accomplishments, and a list of items that carried over or need attention next week.

**Output:** A proposal containing the weekly scorecard. Optionally proposes creating a Google Doc with the scorecard in the team's Weekly Reviews Drive folder.

### 7.5 Natural Language Workflow Creation

Users can create new workflows by describing them in plain English through the dashboard's workflow builder. The description is sent to Claude with a meta-prompt that instructs it to generate a valid `WorkflowDefinition` object.

**Process:**

1. User types a natural language description in the dashboard workflow builder, e.g.: "Every Monday at 9am, check GitHub for any PRs that have been open for more than 3 days and send me a summary with links."
2. The server sends this description to Claude with a meta-prompt that includes the `WorkflowDefinition` TypeScript interface and all available connector names and tool definitions.
3. Claude returns a valid `WorkflowDefinition` JSON object with appropriate cron expression, instruction, and required connectors.
4. The server validates the generated definition (schema check, cron expression parsing, connector availability) and presents it to the user for review.
5. On confirmation, the workflow is saved and scheduled.

**Meta-prompt excerpt:**
> You are a workflow definition generator. Given a natural language description of an automated workflow, produce a valid WorkflowDefinition JSON object. Available connectors: [list]. Available tools per connector: [list]. Map the user's intent to the appropriate trigger type, cron schedule, connectors, and a detailed instruction prompt that a separate Claude instance will use to execute the workflow.

This capability means the workflow library grows organically as the team identifies new repetitive patterns in their work.

---

## 8. Claude Integration

### 8.1 System Prompts

Each workflow execution begins with a system prompt constructed from the workflow's `instruction` field, augmented with contextual metadata:

```
System prompt structure:
  [Workflow instruction from WorkflowDefinition.instruction]
  ---
  Current date/time: {ISO timestamp}
  Active connectors: {comma-separated list}
  Available tools: {tool names from required connectors}
  ---
  Important: When you have gathered enough information, respond with a structured
  proposal in the specified JSON format. Do not take actions directly — only
  propose them for human approval.
```

The trailing instruction ensures Claude always outputs proposals rather than attempting to execute actions on its own. Even though Claude could call write-capable tools (like `create_document`) during its agentic loop, the system prompt directs it to include those as proposed actions in its response instead.

### 8.2 Tool Definitions

Tool definitions are collected at runtime from the connectors listed in the workflow's `requiredConnectors` array. Each connector's `getTools()` method returns an array of Anthropic-compatible tool definitions with `name`, `description`, and `input_schema` fields. These are passed directly to the Claude SDK's `messages.create()` call.

Tool names are globally unique by convention: each connector prefixes its tool names with the connector name (e.g., `calendar_list_events`, `gmail_search_messages`). This prevents collisions when multiple connectors are active in a single workflow.

### 8.3 Agentic Tool-Use Loop

The orchestrator implements the standard Anthropic agentic loop pattern:

```typescript
async function runAgenticLoop(
  systemPrompt: string,
  tools: ToolDefinition[],
  connectors: Map<string, ConnectorPlugin>
): Promise<ClaudeResponse> {
  let messages: Message[] = [];

  while (true) {
    const response = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 4096,
      system: systemPrompt,
      tools: tools,
      messages: messages,
    });

    // If Claude responds with text only (no tool calls), we're done
    if (response.stop_reason === "end_turn") {
      return extractProposal(response);
    }

    // If Claude wants to use tools, execute each tool call
    if (response.stop_reason === "tool_use") {
      const toolResults = [];

      for (const block of response.content) {
        if (block.type === "tool_use") {
          const connector = findConnectorForTool(block.name, connectors);
          const result = await connector.executeTool(block.name, block.input);
          toolResults.push({
            type: "tool_result",
            tool_use_id: block.id,
            content: JSON.stringify(result),
          });
        }
      }

      // Add Claude's response and tool results to messages, then loop
      messages.push({ role: "assistant", content: response.content });
      messages.push({ role: "user", content: toolResults });
    }
  }
}
```

The loop continues until Claude returns a final response without tool calls. Read-only tool calls (listing events, searching emails, fetching file content) execute immediately during the loop. Write-capable tool calls (creating documents, sending emails) are not executed during the loop — instead, Claude is instructed to include them as proposed actions in its final response.

### 8.4 Structured Output for Proposals

Claude's final response is expected to contain a JSON block with the proposal structure:

```json
{
  "summary": "Daily plan for Monday, 2026-03-03",
  "reasoning": "You have 3 meetings today, 5 unread emails (1 from Johannes marked urgent), and 2 PRs awaiting review.",
  "actions": [
    {
      "connector": "google-drive",
      "tool": "create_document",
      "parameters": {
        "title": "Meeting Prep - GMP4U Sync 2026-03-03",
        "content": "..."
      },
      "description": "Create meeting prep doc for the 14:00 GMP4U sync"
    }
  ]
}
```

The orchestrator parses this JSON from Claude's response, validates it against the `Proposal` schema, and creates the proposal record. If Claude's response does not contain valid JSON, the orchestrator retries once with an explicit instruction to format the output correctly.

---

## 9. Dashboard Architecture

### 9.1 Application Structure

The dashboard is a React SPA built with Vite and TypeScript. It runs on `localhost:5173` in development and is served as static files by the Express server in production.

```
dashboard/
  src/
    App.tsx                 # Root component with sidebar navigation
    pages/
      ApprovalQueue.tsx     # Pending proposals awaiting human decision
      WorkflowManager.tsx   # View, enable/disable, and create workflows
      ConnectorStatus.tsx   # Health status of all registered connectors
      ActivityFeed.tsx      # Chronological log of all workflow runs and proposals
    components/
      ProposalCard.tsx      # Single proposal with approve/reject buttons
      WorkflowBuilder.tsx   # Natural language workflow creation form
      ConnectorBadge.tsx    # Status indicator for a single connector
      ActionDetail.tsx      # Expandable view of a proposed action
    hooks/
      useSSE.ts             # Hook for subscribing to SSE event stream
      useProposals.ts       # Hook for fetching and mutating proposals
    types/
      index.ts              # Shared TypeScript types (Proposal, Workflow, etc.)
```

### 9.2 Pages

**Approval Queue:** The primary operational view. Displays all proposals with `pending_approval` status, ordered by creation time (newest first). Each proposal card shows the workflow name, summary, reasoning, and a list of proposed actions. The operator can expand each action to inspect parameters. Two buttons: Approve (executes all actions) and Reject (archives with no action). After approval, the card transitions to show execution status in real time.

**Workflow Manager:** Lists all registered workflow definitions with their trigger type, schedule, required connectors, and enabled/disabled toggle. Includes a "Create Workflow" button that opens the natural language workflow builder. Existing workflows can be edited (modifying the instruction text or schedule) or deleted.

**Connector Status:** Shows each registered connector as a card with its name, description, connection status (connected/disconnected/error), last health check time, and a list of its registered tools. Useful for diagnosing why a workflow failed (e.g., expired OAuth token).

**Activity Feed:** A chronological log of all system events — workflow triggers, proposal creations, approvals, rejections, execution results, and errors. Each entry is timestamped and linkable. Acts as the system's operational audit trail.

### 9.3 Real-Time Updates

The dashboard establishes an SSE connection to `GET /api/events` on mount. The server pushes events for:

- `proposal:created` — new proposal ready for review
- `proposal:updated` — proposal status changed (approved, executing, completed, failed)
- `workflow:triggered` — a workflow has started running
- `connector:status` — a connector's health status changed

The `useSSE` hook manages the EventSource lifecycle, handles reconnection on disconnect, and dispatches events to the appropriate React state handlers.

### 9.4 REST Interactions

Actions that mutate state (approve, reject, create workflow, toggle connector) use standard REST calls to the Express API. The dashboard does not poll — all state updates arrive via SSE. REST is used only for user-initiated actions.

---

## 10. Scheduling & Events

### 10.1 Cron-Based Triggers

The `node-cron` library handles time-based workflow triggers. At server startup, the scheduler iterates over all enabled workflow definitions with `trigger.type === "cron"` and registers a cron job for each:

```typescript
import cron from "node-cron";

for (const workflow of enabledWorkflows) {
  if (workflow.trigger.type === "cron" && workflow.trigger.schedule) {
    cron.schedule(workflow.trigger.schedule, () => {
      workflowEngine.run(workflow);
    });
  }
}
```

Cron expressions use the standard five-field format: minute, hour, day-of-month, month, day-of-week. All times are in the server's local timezone.

### 10.2 Event-Driven Triggers

The orchestrator uses Node.js's built-in `EventEmitter` for event-driven workflow triggers. Workflows with `trigger.type === "event"` subscribe to named events:

```typescript
for (const workflow of enabledWorkflows) {
  if (workflow.trigger.type === "event" && workflow.trigger.eventName) {
    eventBus.on(workflow.trigger.eventName, (payload) => {
      workflowEngine.run(workflow, payload);
    });
  }
}
```

Events are emitted by background processes. For example, a calendar polling loop runs every 15 minutes, compares the current calendar state to the previous state, and emits `meeting:approaching` events when a meeting is 30 minutes away:

```typescript
async function pollCalendar(): Promise<void> {
  const events = await calendarConnector.executeTool("calendar_get_upcoming_meetings", { count: 3 });
  for (const event of events) {
    const minutesUntil = differenceInMinutes(new Date(event.start), new Date());
    if (minutesUntil <= 30 && minutesUntil > 15) {
      eventBus.emit("meeting:approaching", { event });
    }
  }
}

setInterval(pollCalendar, 15 * 60 * 1000);
```

### 10.3 Dynamic Scheduling

Some workflows require dynamic scheduling that depends on runtime data. The Meeting Prep workflow is the primary example: its trigger time depends on today's calendar, which is not known at server startup.

The orchestrator handles this by running a daily scheduling pass at 00:05 that reads today's calendar and creates one-time scheduled jobs for each qualifying meeting. These jobs are discarded at end of day and regenerated the next morning.

---

## 11. Security & Credentials

### 11.1 Credential Management

All secrets are stored in a `.env` file at the project root. This file is listed in `.gitignore` and is never committed to version control.

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Authentication for Claude API calls |
| `GOOGLE_CLIENT_ID` | OAuth2 client ID for Google APIs |
| `GOOGLE_CLIENT_SECRET` | OAuth2 client secret for Google APIs |
| `GOOGLE_REFRESH_TOKEN` | Long-lived refresh token for offline access to Calendar, Gmail, and Drive |
| `GITHUB_TOKEN` | GitHub personal access token with `repo` scope |

### 11.2 Google OAuth2

The orchestrator uses a single OAuth2 client for all Google API access (Calendar, Gmail, Drive). The initial OAuth2 flow is performed once via a setup script that opens a browser, obtains user consent, and saves the refresh token. Subsequent API calls use the refresh token to obtain short-lived access tokens automatically via the `googleapis` library's built-in token refresh mechanism.

Scopes requested:
- `https://www.googleapis.com/auth/calendar.readonly`
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/drive` (read + write for document creation)

### 11.3 Network Security

The orchestrator runs exclusively on `localhost`. The Express server binds to `127.0.0.1:3000` and the Vite dev server to `127.0.0.1:5173`. Neither is exposed to the network or the internet. There is no authentication layer on the local API because the threat model assumes only the local operator has access.

If the orchestrator is ever deployed to a shared server, an authentication layer (session-based or token-based) must be added before exposing any endpoints.

### 11.4 Data Handling

The orchestrator processes data transiently. Workflow results and proposals are held in memory and lost on server restart. No persistent database is used in the initial implementation. Email content, calendar details, and document text are read from APIs, passed through Claude for analysis, and included in proposals. No data is cached or stored beyond the current server session.

This transient design is intentional: it minimizes the attack surface and avoids creating a secondary data store that could contain sensitive information. Persistent storage is a future enhancement (see Section 13).

---

## 12. API Reference

All endpoints are served from `http://localhost:3000`.

### Proposals

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/proposals` | List all proposals. Supports `?status=pending_approval` query filter. |
| `GET` | `/api/proposals/:id` | Get a single proposal by ID. |
| `POST` | `/api/proposals/:id/approve` | Approve a pending proposal. Transitions to `executing`, then `completed` or `failed`. |
| `POST` | `/api/proposals/:id/reject` | Reject a pending proposal. Transitions to `rejected`. |

### Workflows

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/workflows` | List all registered workflow definitions. |
| `GET` | `/api/workflows/:id` | Get a single workflow definition by ID. |
| `POST` | `/api/workflows` | Create a new workflow definition. Body: `WorkflowDefinition` JSON. |
| `PUT` | `/api/workflows/:id` | Update an existing workflow definition. |
| `DELETE` | `/api/workflows/:id` | Delete a workflow definition and unschedule it. |
| `POST` | `/api/workflows/:id/trigger` | Manually trigger a workflow, bypassing its schedule. |
| `POST` | `/api/workflows/generate` | Generate a workflow definition from natural language. Body: `{ description: string }`. Returns a `WorkflowDefinition` for review. |

### Connectors

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/connectors` | List all registered connectors with status. |
| `GET` | `/api/connectors/:name` | Get a single connector's details, tools, and status. |
| `GET` | `/api/connectors/:name/tools` | List all tools registered by a connector. |

### Events (SSE)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/events` | SSE stream. Emits `proposal:created`, `proposal:updated`, `workflow:triggered`, `connector:status` events. |

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Server health check. Returns uptime, active connectors count, and pending proposals count. |

---

## 13. Future Extensibility

### 13.1 Additional Connectors

The plugin architecture is designed to accommodate new connectors without modifying core orchestrator code. Planned connectors include:

- **Slack:** Channel monitoring, message sending, thread summaries. Enables workflows like "summarize today's #engineering channel and post key decisions to Drive."
- **Notion:** Page and database access. Useful for teams that maintain knowledge bases or sprint boards in Notion.
- **Linear:** Issue tracking integration. Enables workflows that correlate GitHub PRs with Linear issues and track cycle time.
- **Jira:** For teams using Jira for project management. Similar to Linear but targeting enterprise customers who have existing Jira workflows.

### 13.2 Tier 3 Strategic Layer

The Tier 3 agent would operate on a weekly or monthly cadence, consuming accumulated data from Tier 2 outputs:

- Historical proposals and their approval rates (what does the team consistently approve vs. reject?)
- Weekly scorecards (are meeting hours trending up? Is commit velocity stable?)
- Cross-tool correlation (do weeks with more partner emails correlate with slower development velocity?)

Tier 3 would use a more capable model (Claude Opus) and produce strategic recommendations: "You spent 40% of this month in meetings. Consider consolidating the three weekly GMP4U syncs into a single bi-weekly session with a shared document."

### 13.3 Persistent Storage

The current in-memory design is suitable for a single-operator prototype. For production use, the orchestrator should migrate to a persistent store:

- **SQLite** for single-machine deployment (simplest migration path — no external dependencies).
- **PostgreSQL** for multi-user or server deployment (aligns with BioNexus's existing PostgreSQL infrastructure).

Persistence enables historical analytics, proposal audit trails, and workflow performance metrics over time.

### 13.4 Multi-User Support

The current architecture assumes a single operator. Multi-user support would require:

- Authentication on the Express API (JWT or session-based, consistent with BioNexus platform auth).
- Per-user connector credentials (each user connects their own Google account and GitHub token).
- Per-user workflow definitions and proposal queues.
- Role-based access: some users can create workflows, all users can approve proposals for their own workflows.

---

*End of document.*
