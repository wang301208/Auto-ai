import React from 'react';
import { Box, Text } from 'ink';
import type { CompletionItem } from '../types.js';
import { theme } from '../theme.js';

interface Props {
  active: number;
  items: CompletionItem[];
}

export default function CompletionList({ active, items }: Props) {
  if (!items.length) return null;

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={theme.border} paddingX={1} marginBottom={1}>
      {items.slice(0, 8).map((item, index) => (
        <Text color={index === active ? theme.prompt : theme.text} key={`${item.text}:${index}`}>
          {index === active ? '>' : '  '}
          {item.display || item.text}
          {item.meta ? <Text color={theme.dim}>  {item.meta}</Text> : null}
        </Text>
      ))}
    </Box>
  );
}


