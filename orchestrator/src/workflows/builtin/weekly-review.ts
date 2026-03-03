import type { WorkflowDefinition } from '../types.js';

export const weeklyReview: WorkflowDefinition = {
  id: 'builtin-weekly-review',
  name: 'Weekly Review',
  description: 'Auto-generate a weekly scorecard from calendar events, git commits, and PR activity.',
  enabled: true,
  trigger: { type: 'cron', cron: '0 17 * * 5' },
  instruction: `You are a weekly review assistant for BioNexus.

Your task:
1. Use list_events to get all calendar events from the past 7 days
2. Use list_recent_commits to get all git commits from the past 7 days
3. Use list_pull_requests to get all PR activity (open and recently closed)

Generate a weekly scorecard with these sections:

**Meetings & Collaboration:**
- Total meetings attended
- Key meetings and outcomes

**Development Activity:**
- Commits this week (count and highlights)
- PRs opened, merged, and pending review

**Key Deliverables:**
- What was shipped or completed

**Focus Areas for Next Week:**
- Based on open PRs, upcoming meetings, and recent trends

**Productivity Score:**
- A qualitative assessment (Highly Productive / Productive / Needs Improvement)
- Brief explanation of the rating

Call propose_plan with the formatted scorecard.`,
  requiredConnectors: ['google-calendar', 'github'],
  source: 'builtin',
};
