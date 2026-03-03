import type { WorkflowDefinition } from '../types.js';

export const meetingPrep: WorkflowDefinition = {
  id: 'builtin-meeting-prep',
  name: 'Meeting Prep',
  description: 'Before any meeting, auto-draft preparation notes from relevant Drive docs and recent emails.',
  enabled: true,
  trigger: { type: 'cron', cron: '*/30 * * * 1-5' },
  instruction: `You are a meeting preparation assistant for BioNexus.

Your task:
1. Use get_upcoming_meetings to find meetings happening within the next 30 minutes
2. For each upcoming meeting:
   a. Extract the meeting title, attendees, and description
   b. Use search_files on Drive to find related documents (search by keywords from the meeting title/description)
   c. Use search_messages on Gmail to find recent email threads with the meeting attendees
   d. If relevant Drive docs are found, use get_file_content to read key sections
3. Draft concise preparation notes for each meeting including:
   - Meeting context and purpose
   - Key points from relevant documents
   - Recent email context with attendees
   - Suggested talking points or questions

If no meetings are upcoming, simply note that no prep is needed.

Call propose_plan with your meeting prep notes.`,
  requiredConnectors: ['google-calendar', 'gmail', 'google-drive'],
  source: 'builtin',
};
