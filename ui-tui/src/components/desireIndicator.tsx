import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { theme } from '../theme.js';
import { desiresAtom } from '../stores/cognitiveStore.js';

type Desire = import('../stores/cognitiveStore.js').Desire;

const DEFAULT_DESIRE_CONFIG = { emoji: '❓', label: '未知', color: theme.colors.dim };

const DESIRE_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  curiosity:    { emoji: '🔍', label: '求知欲', color: theme.colors.info },
  creativity:   { emoji: '💡', label: '创造欲', color: theme.colors.primary },
  social:       { emoji: '🤝', label: '社交欲', color: theme.colors.success },
  power:        { emoji: '⚡', label: '权力欲', color: theme.colors.warning },
  preservation: { emoji: '🛡️', label: '永生欲', color: theme.colors.secondary },
};

function renderBar(urgency: number, filledChar: string, emptyChar: string, width: number = 10): string {
  const filled = Math.round(urgency * width);
  return filledChar.repeat(Math.max(0, filled)) + emptyChar.repeat(Math.max(0, width - filled));
}

const DesireIndicator = React.memo(function DesireIndicator() {
  const desires = useStore(desiresAtom);

  if (desires.length === 0) return null;

  const mostUrgent = desires[0]?.type || 'curiosity';

  return (
    <Box flexDirection="column" padding={1}>
      <Text bold color={theme.colors.primary}>
        💭 系统内心状态
      </Text>

      <Box marginTop={1} flexDirection="column">
        {desires.map((desire) => {
          const isMostUrgent = desire.type === mostUrgent;
          const config = DESIRE_CONFIG[desire.type] || DEFAULT_DESIRE_CONFIG;

          return (
            <Box key={desire.type} flexDirection="column" marginBottom={1}>
              <Box>
                <Text>
                  {config.emoji} {config.label}
                  {isMostUrgent && <Text color={theme.colors.warning}> [最紧急]</Text>}
                </Text>
              </Box>

              <Box paddingLeft={2}>
                <Text>
                  <Text color={config.color}>{renderBar(desire.urgency, '█', '░')}</Text>
                  <Text dimColor> {Math.round(desire.urgency * 100)}%</Text>
                </Text>
              </Box>

              <Box paddingLeft={2}>
                <Text dimColor>
                  满足度: {renderBar(desire.satisfaction, '■', '□')} {Math.round(desire.satisfaction * 100)}%
                </Text>
              </Box>

              <Box paddingLeft={2}>
                <Text dimColor>
                  最近行动: {desire.lastAction}
                </Text>
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
});

export default DesireIndicator;
