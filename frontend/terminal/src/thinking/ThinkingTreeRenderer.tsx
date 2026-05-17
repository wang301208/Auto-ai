import { Box, Text } from 'ink';
import { useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { currentChain, selectedNodeId, expandedNodeIds, viewMode } from '../stores';
import { ThinkingChainParser } from './ThinkingChainParser';
import { filterContentSafe } from '../stores';
import type { ThinkingNode, ThinkingNodeType } from '../types';

const NODE_TYPE_ICONS: Record<ThinkingNodeType, string> = {
  analysis: '🔍',
  decision: '🎯',
  risk: '⚠️',
  action: '⚡',
  wait: '⏳'
};

const NODE_STATE_COLORS: Record<string, string> = {
  pending: 'gray',
  processing: 'yellow',
  completed: 'green',
  failed: 'red'
};

interface ThinkingTreeRendererProps {
  level?: number;
}

export function ThinkingTreeRenderer({ level = 0 }: ThinkingTreeRendererProps) {
  const chain = useStore(currentChain);
  const selectedId = useStore(selectedNodeId);
  const expanded = useStore(expandedNodeIds);
  const currentViewMode = useStore(viewMode);

  if (!chain) {
    return (
      <Box>
        <Text dimColor>暂无思维链路数据 / No thinking chain data</Text>
      </Box>
    );
  }

  try {
    const parser = new ThinkingChainParser();
    const { nodeMap, rootChildren } = parser.parse(chain);

    const renderNode = useCallback((nodeId: string, depth: number): React.ReactNode => {
      const node = nodeMap.get(nodeId);
      if (!node) return null;

      const isExpanded = expanded.has(nodeId);
      const isSelected = selectedId === nodeId;
      const children = Array.from(nodeMap.values()).filter(n => n.parentId === nodeId);

      const content = filterContentSafe(node.content);
      const indent = '  '.repeat(depth);
      const confidence = node.metadata && 'confidence' in node.metadata && typeof node.metadata['confidence'] === 'number' ? `${(node.metadata['confidence'] * 100).toFixed(0)}%` : '';

      return (
        <Box key={nodeId} flexDirection="column">
          <Box>
            <Text>{indent}</Text>
            <Text color={children.length > 0 ? 'yellow' : 'gray'}>
              {children.length > 0 ? (isExpanded ? '▼' : '▶') : '•'}
            </Text>
            <Text> </Text>
            <Text>{NODE_TYPE_ICONS[node.type]}</Text>
            <Text> </Text>
            <Text color={isSelected ? 'cyan' : 'white'} bold={isSelected}>
              {content.text}
            </Text>
            {confidence && (
              <Text color="cyan" dimColor>
                {' '}({confidence})
              </Text>
            )}
            <Text color={NODE_STATE_COLORS[node.state]} dimColor>
              {' '}[{node.state}]
            </Text>
          </Box>
          {isExpanded && children.length > 0 && (
            <Box flexDirection="column">
              {children.map(child => renderNode(child.id, depth + 1))}
            </Box>
          )}
        </Box>
      );
    }, [nodeMap, expanded, selectedId]);

    return (
      <Box flexDirection="column" borderStyle="single" borderColor="gray" paddingX={1}>
        {rootChildren.map(rootId => renderNode(rootId, 0))}
      </Box>
    );
  } catch (error) {
    return (
      <Box>
        <Text color="red">思维链路解析失败: {error instanceof Error ? error.message : String(error)}</Text>
      </Box>
    );
  }
}
