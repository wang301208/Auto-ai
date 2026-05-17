import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { negotiationQueue } from '../stores';
import { respondNegotiation } from '../stores';
import { filterContentSafe } from '../stores';
import type { SuggestionAction } from '../types';

export function NegotiationOverlay() {
  const negotiations = useStore(negotiationQueue);

  if (negotiations.length === 0) {
    return null;
  }

  const negotiation = negotiations[0];
  const impactAnalysis = filterContentSafe(negotiation.impactAnalysis);
  const expectedConsumption = filterContentSafe(negotiation.usageEstimate.expectedConsumption);

  const handleResponse = (action: SuggestionAction) => {
    respondNegotiation(negotiation.id, action);
  };

  return (
    <Box borderStyle="round" borderColor="cyan" paddingX={1}>
      <Box flexDirection="column">
        <Box>
          <Text bold color="cyan">🤝 资源协商 / Resource Negotiation</Text>
        </Box>
        <Box>
          <Text>资源类型 / Type: </Text>
          <Text color="yellow">{negotiation.resourceType}</Text>
        </Box>
        <Box>
          <Text>请求量 / Amount: </Text>
          <Text color="yellow">{negotiation.requestedAmount.value} {negotiation.requestedAmount.unit}</Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>预估时间 / Estimated Time:</Text>
        </Box>
        <Box>
          <Text dimColor>{negotiation.usageEstimate.estimatedTime}</Text>
        </Box>
        <Box>
          <Text dimColor>预期消耗 / Expected Consumption:</Text>
        </Box>
        <Box>
          <Text dimColor={expectedConsumption.hasFallback}>{expectedConsumption.text}</Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>影响分析 / Impact Analysis:</Text>
        </Box>
        <Box>
          <Text dimColor={impactAnalysis.hasFallback}>{impactAnalysis.text}</Text>
        </Box>
        <Box marginTop={1}>
          <Text color="green">[Y] 同意 / Agree</Text>
          <Text> </Text>
          <Text color="red">[N] 拒绝 / Reject</Text>
          <Text> </Text>
          <Text color="yellow">[M] 修改 / Modify</Text>
        </Box>
      </Box>
    </Box>
  );
}
