import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../../theme.js';
import type { OverlayState } from '../../types.js';

export const SecretOverlay = React.memo(function SecretOverlay({ overlay }: { overlay: Extract<OverlayState, { type: 'secret' }> }) {
  return (
    <Box borderStyle="round" borderColor={theme.colors.warn} flexDirection="column" paddingX={1} marginTop={1}>
      <Text color={theme.colors.warn} bold>密钥输入</Text>
      <Text>{overlay.prompt}</Text>
      <Text color={theme.colors.dim}>{overlay.env_var}: {'*'.repeat(overlay.value?.length || 0)}</Text>
    </Box>
  );
});

export const SudoOverlay = React.memo(function SudoOverlay({ overlay }: { overlay: Extract<OverlayState, { type: 'sudo' }> }) {
  return (
    <Box borderStyle="round" borderColor={theme.colors.warn} flexDirection="column" paddingX={1} marginTop={1}>
      <Text color={theme.colors.warn} bold>Sudo 密码</Text>
      <Text color={theme.colors.dim}>{'*'.repeat(overlay.value?.length || 0)}</Text>
    </Box>
  );
});
