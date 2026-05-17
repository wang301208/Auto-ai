import React from 'react';
import { Box, Text } from 'ink';
import { glyph, theme } from '../theme.js';

const QueuedMessages = React.memo(function QueuedMessages({ items }: { items: string[] }) {
  if (items.length === 0) return null;

  return (
    <Box flexDirection="column" marginBottom={1}>
      {items.map((item, index) => (
        <Text color={theme.colors.dim} key={`${index}:${item}`}>
          {glyph.queued} 排队 {index + 1}: {item}
        </Text>
      ))}
    </Box>
  );
});

export default QueuedMessages;


