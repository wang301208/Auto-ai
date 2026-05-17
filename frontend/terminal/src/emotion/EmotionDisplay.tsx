import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { currentEmotion, currentTheme } from '../stores';

export function EmotionDisplay() {
  const emotion = useStore(currentEmotion);
  const theme = useStore(currentTheme);

  if (!emotion || !theme) {
    return (
      <Box>
        <Text>😐</Text>
      </Box>
    );
  }

  return (
    <Box>
      <Text>{emotion.emoji}</Text>
    </Box>
  );
}
