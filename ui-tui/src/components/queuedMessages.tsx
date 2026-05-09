import React from 'react';
import { Box, Text } from 'ink';
import { glyph, theme } from '../theme.js';

export default function QueuedMessages({ items }: { items: string[] }) {
  if (items.length === 0) return null;

  return (
    <Box flexDirection="column" marginBottom={1}>
      {items.map((item, index) => (
        <Text color={theme.dim} key={`${index}:${item}`}>
          {glyph.queued} queued {index + 1}: {item}
        </Text>
      ))}
    </Box>
  );
}


