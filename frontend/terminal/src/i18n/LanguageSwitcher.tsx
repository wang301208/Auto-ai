import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { currentMode, switchLanguage } from '../stores';

export function LanguageSwitcher() {
  const mode = useStore(currentMode);

  return (
    <Box>
      <Text color="gray">语言 / Language: </Text>
      <Text color={mode === 'zh' ? 'green' : 'gray'}>
        [Z] 中文
      </Text>
      <Text> </Text>
      <Text color={mode === 'bilingual' ? 'green' : 'gray'}>
        [B] 双语
      </Text>
      <Text color="dimColor"> (Ctrl+L)</Text>
    </Box>
  );
}
