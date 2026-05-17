import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { theme } from '../theme.js';
import { activeSuggestions, type ProactiveSuggestion } from '../stores/emotionStore.js';

const PRIORITY_STYLE: Record<string, { color: string; prefix: string }> = {
  high:   { color: theme.colors.error,    prefix: '❗' },
  medium: { color: theme.colors.warning,  prefix: '📌' },
  low:    { color: theme.colors.dim,      prefix: '💬' },
};

const TYPE_LABEL: Record<string, string> = {
  action:           '建议执行',
  resource_request: '资源协商',
  insight:          '洞察发现',
  warning:          '风险预警',
};

const SuggestionItem = React.memo(function SuggestionItem({ suggestion, index }: { suggestion: ProactiveSuggestion; index: number }) {
  const style = PRIORITY_STYLE[suggestion.priority] || PRIORITY_STYLE.low;

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text bold color={style.color as any}>
          {suggestion.emoji} [{TYPE_LABEL[suggestion.type] || suggestion.type}]
        </Text>
        <Text> </Text>
        <Text bold>{suggestion.title}</Text>
      </Box>

      <Box paddingLeft={3}>
        <Text dimColor>{suggestion.description}</Text>
      </Box>

      {suggestion.action && (
        <Box paddingLeft={3}>
          <Text color={theme.colors.primary}>
            ⌨ {suggestion.action}
          </Text>
        </Box>
      )}

      {suggestion.resourceType && (
        <Box paddingLeft={3}>
          <Text color={theme.colors.warning}>
            📦 请求{suggestion.resourceType}: {suggestion.resourceAmount}
          </Text>
        </Box>
      )}

      <Box paddingLeft={3}>
        <Text dimColor>
          输入 {index + 1} 接受 | d{index + 1} 忽略
        </Text>
      </Box>
    </Box>
  );
});

const ProactiveSuggestionPanel = React.memo(function ProactiveSuggestionPanel() {
  const suggestions = useStore(activeSuggestions);

  if (suggestions.length === 0) return null;

  return (
    <Box flexDirection="column" paddingX={1} marginTop={1} borderStyle="round" borderColor={theme.colors.primary}>
      <Text bold color={theme.colors.primary}>
        ⚡ 系统主动建议
      </Text>
      <Text dimColor>系统基于当前状态自主提出以下建议：</Text>

      {suggestions.slice(0, 5).map((s, i) => (
        <SuggestionItem key={s.id} suggestion={s} index={i} />
      ))}

      {suggestions.length > 5 && (
        <Text dimColor>  ...还有 {suggestions.length - 5} 条建议</Text>
      )}
    </Box>
  );
});

export default ProactiveSuggestionPanel;
