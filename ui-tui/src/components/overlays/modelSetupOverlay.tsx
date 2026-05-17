import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../../theme.js';
import { MODEL_SETUP_STEP_LABELS } from '../../constants.js';
import type { OverlayState } from '../../types.js';

export const ModelSetupOverlay = React.memo(function ModelSetupOverlay({ overlay }: { overlay: Extract<OverlayState, { type: 'modelSetup' }> }) {
  return (
    <Box borderStyle="round" borderColor={theme.colors.prompt} flexDirection="column" paddingX={1} marginTop={1}>
      <Text color={theme.colors.prompt} bold>自定义模型配置</Text>
      <Text color={theme.colors.dim}>{overlay.provider.name}</Text>
      <Text>
        {MODEL_SETUP_STEP_LABELS[overlay.step] || overlay.step}：
        {overlay.step === 'api_key' && overlay.value
          ? '*'.repeat(overlay.value?.length || 0)
          : (overlay.value || '')}
      </Text>
      <Text color={theme.colors.dim}>按 Enter 确认，Esc 取消</Text>
    </Box>
  );
});
