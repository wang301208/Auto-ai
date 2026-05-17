import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { emotionHistory } from '../stores';
import { filterContentSafe } from '../stores';

export function EmotionHistoryViewer() {
  const history = useStore(emotionHistory);

  if (history.length === 0) {
    return (
      <Box borderStyle="single" borderColor="gray" paddingX={1}>
        <Text dimColor>暂无情绪历史 / No emotion history</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="yellow" paddingX={1}>
      <Box>
        <Text bold color="yellow">情绪历史 / Emotion History</Text>
      </Box>
      {history.map((record, index) => {
        const reason = filterContentSafe(record.triggerReason);
        return (
          <Box key={index}>
            <Text color="gray">{record.timestamp}</Text>
            <Text color="gray"> | </Text>
            <Text color="cyan">{record.previousType}</Text>
            <Text color="gray"> → </Text>
            <Text color="green">{record.type}</Text>
            <Text color="gray"> | </Text>
            <Text dimColor={reason.hasFallback}>{reason.text}</Text>
          </Box>
        );
      })}
    </Box>
  );
}
