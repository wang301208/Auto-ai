import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme.js';

interface DebateNode {
  id: string;
  topic: string;
  initialDecision: string;
  oppositionView: string;
  confidenceBefore: number;
  confidenceAfter: number;
  status: 'active' | 'completed' | 'abandoned';
  blindSpots?: string[];
}

interface ThoughtConflictProps {
  debates: DebateNode[];
}

/**
 * 思维冲突可视化组件 - 展示系统内部的辩论过程
 * 
 * 设计理念：
 * - 透明化AI的"内心挣扎"
 * - 展示多角度思考的价值
 * - 增强用户对决策的信任
 */
export default function ThoughtConflict({ debates }: ThoughtConflictProps) {
  if (debates.length === 0) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text dimColor>
          🧠 当前没有正在进行的内部辩论
        </Text>
      </Box>
    );
  }

  const renderConfidenceChange = (before: number, after: number) => {
    const change = after - before;
    const changePercent = Math.round(change * 100);
    
    let color: string = theme.colors.primary;
    let arrow = '→';
    
    if (change > 0.1) {
      color = theme.colors.success;
      arrow = '↑';
    } else if (change < -0.1) {
      color = theme.colors.warning;
      arrow = '↓';
    }
    
    return (
      <Text>
        <Text>{Math.round(before * 100)}%</Text>
        <Text color={color}> {arrow} {Math.round(after * 100)}%</Text>
        {changePercent !== 0 && (
          <Text dimColor> ({changePercent > 0 ? '+' : ''}{changePercent}%)</Text>
        )}
      </Text>
    );
  };

  const renderStatusBadge = (status: DebateNode['status']) => {
    const badges = {
      active: { emoji: '▶️', label: '进行中', color: theme.colors.primary },
      completed: { emoji: '✅', label: '已完成', color: theme.colors.success },
      abandoned: { emoji: '⏸️', label: '已放弃', color: theme.colors.dim }
    };
    
    const badge = badges[status];
    
    return (
      <Text color={badge.color}>
        {badge.emoji} {badge.label}
      </Text>
    );
  };

  return (
    <Box flexDirection="column" padding={1}>
      {/* 标题 */}
      <Text bold color={theme.colors.primary}>
        🧠 内部辩论监控
      </Text>
      
      <Text dimColor>
        活跃辩论数: {debates.filter(d => d.status === 'active').length}
      </Text>

      {/* 辩论列表 */}
      <Box marginTop={1} flexDirection="column">
        {debates.map((debate, index) => (
          <Box
            key={debate.id}
            borderStyle={debate.status === 'active' ? 'round' : 'single'}
            borderColor={
              debate.status === 'active' 
                ? theme.colors.primary 
                : theme.colors.dim
            }
            padding={1}
            marginBottom={1}
            flexDirection="column"
          >
            {/* 辩论主题和状态 */}
            <Box>
              <Text bold>
                {index + 1}. {debate.topic}
              </Text>
              <Box marginLeft={2}>
                <Text>
                  {renderStatusBadge(debate.status)}
                </Text>
              </Box>
            </Box>

            {/* 初始决策 */}
            <Box marginTop={1} flexDirection="column">
              <Text dimColor>初始立场:</Text>
              <Box paddingLeft={2}>
                <Text>💭 {debate.initialDecision}</Text>
              </Box>
            </Box>

            {/* 反对派观点 */}
            <Box marginTop={1} flexDirection="column">
              <Text dimColor>反对派质疑:</Text>
              <Box paddingLeft={2}>
                <Text color={theme.colors.warning}>
                  ⚖️ {debate.oppositionView}
                </Text>
              </Box>
            </Box>

            {/* 置信度变化 */}
            <Box marginTop={1}>
              <Text dimColor>置信度调整: </Text>
              {renderConfidenceChange(debate.confidenceBefore, debate.confidenceAfter)}
            </Box>

            {/* 认知盲点 */}
            {debate.blindSpots && debate.blindSpots.length > 0 && (
              <Box marginTop={1} flexDirection="column">
                <Text dimColor>发现的认知盲点:</Text>
                {debate.blindSpots.map((blindSpot, idx) => (
                  <Box key={idx} paddingLeft={2}>
                    <Text color={theme.colors.error}>
                      • {blindSpot}
                    </Text>
                  </Box>
                ))}
              </Box>
            )}

            {/* 辩论价值说明 */}
            <Box marginTop={1}>
              <Text dimColor italic>
                💡 通过内部辩论，我发现了{debate.blindSpots?.length || 0}个潜在问题，
                置信度调整了{Math.round((debate.confidenceAfter - debate.confidenceBefore) * 100)}%
              </Text>
            </Box>
          </Box>
        ))}
      </Box>

      {/* 底部说明 */}
      <Box marginTop={1}>
        <Text dimColor italic>
          ℹ️ 内部辩论帮助我发现逻辑漏洞和认知盲区，做出更稳健的决策
        </Text>
      </Box>
    </Box>
  );
}
