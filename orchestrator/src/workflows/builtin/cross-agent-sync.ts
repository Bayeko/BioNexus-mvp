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
- Skip files that are already in Drive (by matching title)

IMPORTANT — for each create_document action in your proposed plan:
- Set the toolCall tool to "google-drive__create_document"
- In the toolCall input, include "github_path" with the file's repo path (e.g. "docs/API_REFERENCE.md") instead of writing placeholder content. The executor will automatically fetch the real file content from GitHub before creating the document.
- Include "title" and "folder_id" (if known) in the toolCall input as normal.

Call propose_plan with your sync recommendations.`,
  requiredConnectors: ['github', 'google-drive'],
  source: 'builtin',
};
