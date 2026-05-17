import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../../theme.js';
import type { OverlayState } from '../../types.js';

export const ClarifyOverlay = React.memo(function ClarifyOverlay({ overlay }: { overlay: Extract<OverlayState, { type: 'clarify' }> }) {
  return (
    <Box borderStyle="round" borderColor={theme.colors.prompt} flexDirection="column" paddingX={1} marginTop={1}>
      <Text color={theme.colors.prompt} bold>需要补充信息</Text>
      <Text>{overlay.question}</Text>
      {overlay.freeText || !overlay.choices ? (
        <Text color={theme.colors.dim}>输入回答，按 Enter 提交：{overlay.value}</Text>
      ) : (
        overlay.choices.map((choice: string, index: number) => (
          <Text
            color={index === overlay.selected ? theme.colors.prompt : theme.colors.text}
            key={`${choice}:${index}`}
          >
            {index === overlay.selected ? '>' : '  '}
            {index + 1}. {choice}
          </Text>
        ))
      )}
    </Box>
  );
});
