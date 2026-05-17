import { Text } from 'ink';
import { useStore } from '@nanostores/react';
import type { BilingualText } from '../types';
import { filterContentSafe } from '../stores';

interface BilingualTextRendererProps {
  content: BilingualText;
  fallbackText?: string;
}

export function BilingualTextRenderer({ content, fallbackText }: BilingualTextRendererProps) {
  const result = filterContentSafe(content);

  return (
    <Text dimColor={result.hasFallback}>
      {result.text}
    </Text>
  );
}
