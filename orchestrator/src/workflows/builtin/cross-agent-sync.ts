import type { WorkflowDefinition } from '../types.js';

export const crossAgentSync: WorkflowDefinition = {
  id: 'builtin-cross-agent-sync',
  name: 'Cross-Agent Sync',
  description: 'When new documents are created in GitHub, suggest syncing them to Google Drive.',
  enabled: true,
  trigger: { type: 'event', event: 'github:poll' },
  instruction: `You are a document synchronization assistant for BioNexus.

Your task:
1. Use list_recently_changed_files to check for new or modified documents in the GitHub repo (especially in docs/ folder)
2. Use search_files on Google Drive to check if these documents already exist there
3. For any new documents not yet in Drive, propose creating them

When proposing actions:
- Only suggest syncing documentation files (.md, .pdf, .docx)
- Suggest appropriate Drive folder names based on the document type
- Include the document title and a brief summary of its content
- Skip files that are already in Drive (by matching title)

Call propose_plan with your sync recommendations.`,
  requiredConnectors: ['github', 'google-drive'],
  source: 'builtin',
};
