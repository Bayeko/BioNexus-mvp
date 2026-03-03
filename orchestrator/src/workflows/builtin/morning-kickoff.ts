import type { WorkflowDefinition } from '../types.js';

export const morningKickoff: WorkflowDefinition = {
  id: 'builtin-morning-kickoff',
  name: 'Morning Kick-off',
  description: 'Scan today\'s calendar, recent emails, and GitHub activity to propose a prioritized daily plan.',
  enabled: true,
  trigger: { type: 'cron', cron: '0 8 * * 1-5' },
  instruction: `You are a daily planning assistant for a biotech startup (BioNexus).

Your task:
1. First, use list_events to get today's calendar events
2. Use list_unread or search_messages to check important recent emails
3. Use list_recent_commits and list_pull_requests to check GitHub activity
4. Based on all this context, propose a prioritized daily plan

The plan should:
- Highlight meetings and their times
- Flag urgent emails that need responses
- Note any PRs that need review
- Suggest time blocks for focused work
- Prioritize items as high/medium/low

Call propose_plan with your recommended daily schedule.`,
  requiredConnectors: ['google-calendar', 'gmail', 'github'],
  source: 'builtin',
};
