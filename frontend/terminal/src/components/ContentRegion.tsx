import { Box } from 'ink';
import { ThinkingTreeRenderer } from '../thinking/ThinkingTreeRenderer';
import { ThinkingNodeDetail } from '../thinking/ThinkingNodeDetail';

export function ContentRegion() {
  return (
    <Box flexDirection="column" flexGrow={1}>
      <ThinkingTreeRenderer />
      <ThinkingNodeDetail />
    </Box>
  );
}
