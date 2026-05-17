import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { currentChain, selectedNodeId } from '../stores';
import { filterContentSafe } from '../stores';

export function ThinkingNodeDetail() {
  const chain = useStore(currentChain);
  const selectedId = useStore(selectedNodeId);

  if (!chain || !selectedId) {
    return (
      <Box borderStyle="single" borderColor="gray" paddingX={1} height={10}>
        <Text dimColor>选择一个节点查看详情 / Select a node to view details</Text>
      </Box>
    );
  }

  const node = chain.nodes.find(n => n.id === selectedId);
  if (!node) {
    return (
      <Box borderStyle="single" borderColor="gray" paddingX={1} height={10}>
        <Text color="red">节点未找到 / Node not found</Text>
      </Box>
    );
  }

  const content = filterContentSafe(node.content);
  const details = node.details ? filterContentSafe(node.details) : null;

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="cyan" paddingX={1} height={15}>
      <Box>
        <Text bold color="cyan">节点详情 / Node Detail</Text>
      </Box>
      <Box>
        <Text>ID: </Text>
        <Text color="yellow">{node.id}</Text>
      </Box>
      <Box>
        <Text>类型 / Type: </Text>
        <Text color="yellow">{node.type}</Text>
      </Box>
      <Box>
        <Text>状态 / State: </Text>
        <Text color="yellow">{node.state}</Text>
      </Box>
      <Box>
        <Text>时间 / Time: </Text>
        <Text color="yellow">{node.timestamp}</Text>
      </Box>
      <Box>
        <Text>内容 / Content:</Text>
      </Box>
      <Box paddingX={1}>
        <Text dimColor={content.hasFallback}>{content.text}</Text>
      </Box>
      {details && (
        <>
          <Box>
            <Text>详情 / Details:</Text>
          </Box>
          <Box paddingX={1}>
            <Text dimColor={details.hasFallback}>{details.text}</Text>
          </Box>
        </>
      )}
      {node.parentId && (
        <Box>
          <Text>父节点 / Parent: </Text>
          <Text color="yellow">{node.parentId}</Text>
        </Box>
      )}
    </Box>
  );
}
