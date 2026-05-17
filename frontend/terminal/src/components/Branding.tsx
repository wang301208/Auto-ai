import { Box, Text } from 'ink';
import { EmotionDisplay } from '../emotion';
import { LanguageSwitcher } from '../i18n';

export function Branding() {
  return (
    <Box borderStyle="single" borderColor="cyan" paddingX={1}>
      <Box flexGrow={1}>
        <Text bold color="cyan">AutoGPT 智能终端 / AutoGPT Intelligent Terminal</Text>
        <Text color="gray"> v1.0.0</Text>
      </Box>
      <Box>
        <EmotionDisplay />
      </Box>
      <Box marginLeft={1}>
        <LanguageSwitcher />
      </Box>
    </Box>
  );
}
