import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { theme } from '../theme.js';
import { emotionAtom, EMOTION_META, type EmotionType } from '../stores/emotionStore.js';

const INTENSITY_BAR_CHARS = ['░', '▒', '▓', '█'];

function renderIntensityBar(intensity: number, width: number = 10): string {
  const filled = Math.round(intensity * width);
  const empty = width - filled;
  return '█'.repeat(Math.max(0, filled)) + '░'.repeat(Math.max(0, empty));
}

function renderConfidenceDot(confidence: number): string {
  if (confidence >= 0.8) return '●';
  if (confidence >= 0.5) return '◐';
  if (confidence >= 0.3) return '○';
  return '◌';
}

function renderEmotionHistory(history: import('../stores/emotionStore.js').EmotionTransition[]): string {
  if (history.length === 0) return '';
  const recent = history.slice(-6);
  return recent.map(t => `${EMOTION_META[t.from].emoji}→${EMOTION_META[t.to].emoji}`).join(' ');
}

const EmotionIndicator = React.memo(function EmotionIndicator() {
  const emotion = useStore(emotionAtom);
  const meta = EMOTION_META[emotion.current];

  const duration = Date.now() - emotion.since;
  const durationStr = duration < 60000
    ? `${Math.round(duration / 1000)}s`
    : `${Math.round(duration / 60000)}m`;

  return (
    <Box flexDirection="column" paddingX={1} marginTop={1}>
      <Box>
        <Text bold color={meta.color as any}>
          {meta.emoji} {meta.label}
        </Text>
        <Text> </Text>
        <Text dimColor>{meta.description}</Text>
      </Box>

      <Box marginTop={0}>
        <Text dimColor>  强度 </Text>
        <Text>{renderIntensityBar(emotion.intensity)}</Text>
        <Text dimColor> </Text>
        <Text dimColor>确信 </Text>
        <Text>{renderConfidenceDot(emotion.confidence)} {Math.round(emotion.confidence * 100)}%</Text>
        <Text dimColor> </Text>
        <Text dimColor>{durationStr}</Text>
      </Box>

      {emotion.reason && (
        <Box>
          <Text dimColor italic>
             💭 {emotion.reason}
          </Text>
        </Box>
      )}

      {emotion.history.length > 2 && (
        <Box>
          <Text dimColor>  轨迹 {renderEmotionHistory(emotion.history)}</Text>
        </Box>
      )}
    </Box>
  );
});

export default EmotionIndicator;
