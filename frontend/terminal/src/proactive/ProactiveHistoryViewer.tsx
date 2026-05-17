import { Box, Text } from 'ink';
import type { ProactiveInteractionRecord } from '../types';
import { filterContentSafe } from '../stores';

interface ProactiveHistoryViewerProps {
  records: ProactiveInteractionRecord[];
}

export function ProactiveHistoryViewer({ records }: ProactiveHistoryViewerProps) {
  if (records.length === 0) {
    return (
      <Box borderStyle="single" borderColor="gray" paddingX={1}>
        <Text dimColor>暂无交互历史 / No interaction history</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="green" paddingX={1}>
      <Box>
        <Text bold color="green">主动交互历史 / Proactive Interaction History</Text>
      </Box>
      {records.map((record, index) => {
        return (
          <Box key={index}>
            <Text color="gray">{record.timestamp}</Text>
            <Text color="gray"> | </Text>
            <Text color={record.type === 'suggestion' ? 'yellow' : 'cyan'}>
              {record.type === 'suggestion' ? '建议' : '协商'}
            </Text>
            <Text color="gray"> | </Text>
            <Text color={record.userAction === 'confirm' ? 'green' : 'red'}>
              {record.userAction === 'confirm' ? '接受' : record.userAction === 'reject' ? '拒绝' : '协商'}
            </Text>
            {record.resourceType && (
              <>
                <Text color="gray"> | </Text>
                <Text color="yellow">{record.resourceType}</Text>
                {record.requestedAmount && (
                  <>
                    <Text color="gray">: </Text>
                    <Text color="white">{record.requestedAmount.value} {record.requestedAmount.unit}</Text>
                  </>
                )}
              </>
            )}
          </Box>
        );
      })}
    </Box>
  );
}
