import { Box, Text } from 'ink';
import { useState } from 'react';
import type { ThinkingHistoryRecord } from '../types';
import { filterContentSafe } from '../stores';

interface ThinkingHistoryViewerProps {
  records: ThinkingHistoryRecord[];
}

export function ThinkingHistoryViewer({ records }: ThinkingHistoryViewerProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  if (records.length === 0) {
    return (
      <Box borderStyle="single" borderColor="gray" paddingX={1}>
        <Text dimColor>暂无历史记录 / No history records</Text>
      </Box>
    );
  }

  const selectedRecord = records[selectedIndex];
  const summary = filterContentSafe(selectedRecord.summary);

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="magenta" paddingX={1}>
      <Box>
        <Text bold color="magenta">思维历史 / Thinking History</Text>
      </Box>
      {records.map((record, index) => {
        const isSelected = index === selectedIndex;
        return (
          <Box key={index}>
            <Text color={isSelected ? 'green' : 'gray'}>
              {isSelected ? '►' : ' '}
            </Text>
            <Text color={isSelected ? 'white' : 'gray'}>
              {record.timestamp}
            </Text>
            <Text color="gray"> | </Text>
            <Text color={isSelected ? 'yellow' : 'gray'}>
              节点: {record.nodeCount}
            </Text>
            <Text color="gray"> | </Text>
            <Text color={isSelected ? 'yellow' : 'gray'}>
              耗时: {record.duration}ms
            </Text>
          </Box>
        );
      })}
      <Box marginTop={1} borderTop>
        <Text bold>摘要 / Summary:</Text>
      </Box>
      <Box paddingX={1}>
        <Text dimColor={summary.hasFallback}>{summary.text}</Text>
      </Box>
    </Box>
  );
}
