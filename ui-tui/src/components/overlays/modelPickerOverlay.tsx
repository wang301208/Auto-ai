import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../../theme.js';
import type { OverlayState, ModelProvider } from '../../types.js';

export const ModelPickerOverlay = React.memo(function ModelPickerOverlay({ overlay }: { overlay: Extract<OverlayState, { type: 'modelPicker' }> }) {
  return (
    <Box borderStyle="round" borderColor={theme.colors.prompt} flexDirection="column" paddingX={1} marginTop={1}>
      <Text color={theme.colors.prompt} bold>选择模型</Text>
      {overlay.providers.map((provider: ModelProvider, index: number) => (
        <Text
          color={index === overlay.selected ? theme.colors.prompt : theme.colors.text}
          key={provider.slug}
        >
          {index === overlay.selected ? '>' : '  '}
          {provider.name}{' '}
          <Text color={theme.colors.dim}>
            {(provider.models || []).join(', ')}
          </Text>
        </Text>
      ))}
    </Box>
  );
});
