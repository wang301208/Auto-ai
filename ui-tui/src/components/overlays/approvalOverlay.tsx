import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../../theme.js';
import { TIMEOUTS, APPROVAL_CHOICES, APPROVAL_CHOICE_LABELS } from '../../constants.js';
import type { OverlayState } from '../../types.js';

export const ApprovalOverlay = React.memo(function ApprovalOverlay({ overlay }: { overlay: Extract<OverlayState, { type: 'approval' }> }) {
  return (
    <Box borderStyle="round" borderColor={theme.colors.warn} flexDirection="column" paddingX={1} marginTop={1}>
      <Text color={theme.colors.warn} bold>需要审批</Text>
      <Text>{overlay.command || '操作'}</Text>
      {overlay.description ? <Text color={theme.colors.dim}>{overlay.description}</Text> : null}
      {typeof overlay.timeout_remaining === 'number' ? (
        <Text color={theme.colors.dim}>
          {overlay.timeout_remaining}s 后自动同意，{TIMEOUTS.APPROVAL} 秒未操作将自动同意
        </Text>
      ) : null}
      <Text>
        {APPROVAL_CHOICES.map((choice: string, index: number) =>
          `${index === overlay.selected ? '>' : ' '} ${APPROVAL_CHOICE_LABELS[choice]}`
        ).join('  ')}
      </Text>
    </Box>
  );
});
