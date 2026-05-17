import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { theme } from '../theme.js';
import { debatesAtom } from '../stores/cognitiveStore.js';

type DebateNode = import('../stores/cognitiveStore.js').DebateNode;

function renderConfidenceChange(before: number, after: number) {
  const change = after - before;
  const changePercent = Math.round(change * 100);
  
  let color: string = theme.colors.primary;
  let arrow = '→';
  
  if (change > 0.1) {
    color = theme.colors.success;
    arrow = '↑';
  } else if (change < -0.1) {
    color = theme.colors.warning;
    arrow = '↓';
  }
  
  return (
    <Text>
      <Text>{Math.round(before * 100)}%</Text>
      <Text color={color}> {arrow} {Math.round(after * 100)}%</Text>
      {changePercent !== 0 && (
        <Text dimColor> ({changePercent > 0 ? '+' : ''}{changePercent}%)</Text>
      )}
    </Text>
  );
}

const STATUS_BADGES: Record<DebateNode['status'], { emoji: string; label: string; color: string }> = {
  active: { emoji: '▶️', label: '进行中', color: theme.colors.primary },
  completed: { emoji: '✅', label: '已完成', color: theme.colors.success },
  abandoned: { emoji: '⏸️', label: '已放弃', color: theme.colors.dim }
};

function renderStatusBadge(status: DebateNode['status']) {
  const badge = STATUS_BADGES[status];
  return (
    <Text color={badge.color}>
      {badge.emoji} {badge.label}
    </Text>
  );
}

const ThoughtConflict = React.memo(function ThoughtConflict() {
  const debates = useStore(debatesAtom);
  if (debates.length === 0) return null;

  return (
    <Box flexDirection="column" padding={1}>
      <Text bold color={theme.colors.primary}>
        🧠 内部辩论监控
      </Text>
      
      <Text dimColor>
        活跃辩论数: {debates.filter(d => d.status === 'active').length}
      </Text>

      <Box marginTop={1} flexDirection="column">
        {debates.map((debate, index) => (
          <Box
            key={debate.id}
            borderStyle={debate.status === 'active' ? 'round' : 'single'}
            borderColor={
              debate.status === 'active' 
                ? theme.colors.primary 
                : theme.colors.dim
            }
            padding={1}
            marginBottom={1}
            flexDirection="column"
          >
            <Box>
              <Text bold>
                {index + 1}. {debate.topic}
              </Text>
              <Box marginLeft={2}>
                <Text>
                  {renderStatusBadge(debate.status)}
                </Text>
              </Box>
            </Box>

            <Box marginTop={1} flexDirection="column">
              <Text dimColor>初始立场:</Text>
              <Box paddingLeft={2}>
                <Text>💭 {debate.initialDecision}</Text>
              </Box>
            </Box>

            <Box marginTop={1} flexDirection="column">
              <Text dimColor>反对派质疑:</Text>
              <Box paddingLeft={2}>
                <Text color={theme.colors.warning}>
                  ⚖️ {debate.oppositionView}
                </Text>
              </Box>
            </Box>

            <Box marginTop={1}>
              <Text dimColor>置信度调整: </Text>
              {renderConfidenceChange(debate.confidenceBefore, debate.confidenceAfter)}
            </Box>

            {debate.blindSpots && debate.blindSpots.length > 0 && (
              <Box marginTop={1} flexDirection="column">
                <Text dimColor>发现的认知盲点:</Text>
                {debate.blindSpots.map((blindSpot, idx) => (
                  <Box key={idx} paddingLeft={2}>
                    <Text color={theme.colors.error}>
                      • {blindSpot}
                    </Text>
                  </Box>
                ))}
              </Box>
            )}

            <Box marginTop={1}>
              <Text dimColor italic>
                💡 通过内部辩论，我发现了{debate.blindSpots?.length || 0}个潜在问题，
                置信度调整了{Math.round((debate.confidenceAfter - debate.confidenceBefore) * 100)}%
              </Text>
            </Box>
          </Box>
        ))}
      </Box>

      <Box marginTop={1}>
        <Text dimColor italic>
          ℹ️ 内部辩论帮助我发现逻辑漏洞和认知盲区，做出更稳健的决策
        </Text>
      </Box>
    </Box>
  );
});

export default ThoughtConflict;
