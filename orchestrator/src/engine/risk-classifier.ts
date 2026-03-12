import type { ProposedAction, RiskLevel, RiskOverride } from '../store/types.js';

/** Tool name patterns for each built-in risk level */
const GREEN_PATTERNS = [
  /list/i,
  /get/i,
  /search/i,
  /read/i,
  /fetch/i,
  /view/i,
  /describe/i,
  /report/i,
];

const YELLOW_PATTERNS = [
  /create_document/i,
  /create_folder/i,
  /upload/i,
  /update_event/i,
  /create_event/i,
  /update_file/i,
];

const RED_PATTERNS = [
  /send_email/i,
  /send_message/i,
  /gmail/i,
  /delete/i,
  /compliance/i,
];

/** Description keywords that force red */
const RED_DESCRIPTION_KEYWORDS = [
  /send.*email/i,
  /external.*part/i,
  /compliance/i,
  /regulatory/i,
  /notify.*external/i,
];

function matchesPatterns(value: string, patterns: RegExp[]): boolean {
  return patterns.some((p) => p.test(value));
}

/**
 * Classify a single action's risk level based on its tool call, connector, and description.
 * Custom overrides take precedence over built-in rules.
 */
export function classifyAction(
  action: ProposedAction,
  overrides: RiskOverride[],
): RiskLevel {
  const toolName = action.toolCall?.tool ?? '';
  const description = action.description;
  const input = action.toolCall?.input ?? {};

  // Check custom overrides first (most specific wins)
  for (const override of overrides) {
    const pattern = override.pattern.toLowerCase();
    const searchSpace = [
      toolName,
      description,
      action.connector ?? '',
      JSON.stringify(input),
    ].join(' ').toLowerCase();

    if (searchSpace.includes(pattern)) {
      return override.riskLevel;
    }
  }

  // Check red patterns first (most restrictive)
  if (toolName && matchesPatterns(toolName, RED_PATTERNS)) return 'red';
  if (matchesPatterns(description, RED_DESCRIPTION_KEYWORDS)) return 'red';

  // Check yellow patterns
  if (toolName && matchesPatterns(toolName, YELLOW_PATTERNS)) return 'yellow';

  // Check green patterns
  if (toolName && matchesPatterns(toolName, GREEN_PATTERNS)) return 'green';

  // Default: if there's a tool call we don't recognize, be cautious
  if (toolName) return 'yellow';

  // Actions without tool calls (informational) are green
  return 'green';
}

/**
 * Get the highest risk level across all actions.
 * red > yellow > green
 */
export function getProposalRiskLevel(actions: ProposedAction[]): RiskLevel {
  const levels = actions.map((a) => a.riskLevel ?? 'green');
  if (levels.includes('red')) return 'red';
  if (levels.includes('yellow')) return 'yellow';
  return 'green';
}

/**
 * Classify all actions in a proposal and return them with riskLevel set.
 */
export function classifyProposalActions(
  actions: ProposedAction[],
  overrides: RiskOverride[],
): ProposedAction[] {
  return actions.map((action) => ({
    ...action,
    riskLevel: classifyAction(action, overrides),
  }));
}
