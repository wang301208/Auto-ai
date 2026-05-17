import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { suggestionQueue } from '../stores';
import { respondSuggestion } from '../stores';
import { filterContentSafe } from '../stores';
import type { SuggestionAction } from '../types';

export function SuggestionOverlay() {
  const suggestions = useStore(suggestionQueue);

  if (suggestions.length === 0) {
    return null;
  }

  const suggestion = suggestions[0];
  const content = filterContentSafe(suggestion.content);
  const expectedEffect = filterContentSafe(suggestion.expectedEffect);
  const metadata = suggestion.metadata && typeof suggestion.metadata === 'object' ? suggestion.metadata as Record<string, unknown> : null;
  const desireType = metadata?.['desire_type'] as string || '';
  const urgency = metadata?.['urgency'] as number ? (metadata['urgency'] as number).toFixed(2) : '';
  const timestamp = metadata?.['timestamp'] as string ? new Date(metadata['timestamp'] as string).toLocaleTimeString() : '';

  const handleResponse = (action: SuggestionAction) => {
    respondSuggestion(suggestion.id, action);
  };

  return (
    <Box borderStyle="round" borderColor="yellow" paddingX={1}>
      <Box flexDirection="column">
        <Box>
          <Text bold color="yellow">💡 建议 / Suggestion</Text>
          {timestamp && (
            <Text dimColor>
              {' '}({timestamp})
            </Text>
          )}
        </Box>
        <Box>
          <Text dimColor={content.hasFallback}>{content.text}</Text>
        </Box>
        {desireType && (
          <Box marginTop={1}>
            <Text dimColor>Desire: {desireType}</Text>
            {urgency && (
              <Text dimColor>
                {' '}Urgency: {urgency}
              </Text>
            )}
          </Box>
        )}
        <Box marginTop={1}>
          <Text dimColor>预期效果 / Expected Effect:</Text>
        </Box>
        <Box>
          <Text dimColor={expectedEffect.hasFallback}>{expectedEffect.text}</Text>
        </Box>
        <Box marginTop={1}>
          <Text color="green">[Y] 确认 / Confirm</Text>
          <Text> </Text>
          <Text color="red">[N] 拒绝 / Reject</Text>
        </Box>
      </Box>
    </Box>
  );
}
