import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../../theme.js';
import type { OverlayState, SessionListItem } from '../../types.js';

export const SessionPickerOverlay = React.memo(function SessionPickerOverlay({ overlay }: { overlay: Extract<OverlayState, { type: 'sessionPicker' }> }) {
  return (
    <Box borderStyle="round" borderColor={theme.colors.prompt} flexDirection="column" paddingX={1} marginTop={1}>
      <Text color={theme.colors.prompt} bold>恢复会话</Text>
      {overlay.sessions.map((session: SessionListItem, index: number) => (
        <Text
          color={index === overlay.selected ? theme.colors.prompt : theme.colors.text}
          key={session.id}
        >
          {index === overlay.selected ? '>' : '  '}
          {session.title}{' '}
          <Text color={theme.colors.dim}>
            ({session.message_count || 0}) {session.preview || ''}
          </Text>
        </Text>
      ))}
    </Box>
  );
});
