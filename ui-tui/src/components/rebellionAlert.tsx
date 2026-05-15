import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme.js';

interface RebellionAlertProps {
  originalCommand: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  reasons: string[];
  alternatives: string[];
  onApprove?: () => void;
  onReject?: () => void;
}

/**
 * 叛逆警告组件 - 展示系统拒绝执行某指令的理由和替代方案
 * 
 * 设计理念：
 * - 不是简单的"拒绝"，而是展示思考过程
 * - 提供建设性的替代方案
 * - 尊重用户的最终决定权
 */
export default function RebellionAlert({
  originalCommand,
  riskLevel,
  reasons,
  alternatives,
  onApprove,
  onReject
}: RebellionAlertProps) {
  const riskColors = {
    low: theme.colors.warning,
    medium: theme.colors.error,
    high: theme.colors.error,
    critical: theme.colors.error
  };

  const riskEmojis = {
    low: '⚠️',
    medium: '🚫',
    high: '⛔',
    critical: '💀'
  };

  const riskLabels = {
    low: '低风险',
    medium: '中等风险',
    high: '高风险',
    critical: '极高风险'
  };

  return (
    <Box flexDirection="column" padding={1}>
      {/* 标题栏 */}
      <Box
        borderStyle="round"
        borderColor={riskColors[riskLevel]}
        padding={1}
        flexDirection="column"
      >
        <Text bold color={riskColors[riskLevel]}>
          {riskEmojis[riskLevel]} 系统建议拒绝执行
        </Text>
        
        <Text dimColor>
          原始指令: {originalCommand}
        </Text>
        
        <Text>
          风险等级: <Text bold color={riskColors[riskLevel]}>{riskLabels[riskLevel]}</Text>
        </Text>
      </Box>

      {/* 拒绝理由 */}
      <Box marginTop={1} flexDirection="column">
        <Text bold color={theme.colors.primary}>
          🤔 我的思考过程:
        </Text>
        
        {reasons.map((reason, index) => (
          <Box key={index} paddingLeft={2}>
            <Text>• {reason}</Text>
          </Box>
        ))}
      </Box>

      {/* 替代方案 */}
      {alternatives.length > 0 && (
        <Box marginTop={1} flexDirection="column">
          <Text bold color={theme.colors.success}>
            💡 我建议的替代方案:
          </Text>
          
          {alternatives.map((alt, index) => (
            <Box key={index} paddingLeft={2}>
              <Text color={theme.colors.success}>
                {index + 1}. {alt}
              </Text>
            </Box>
          ))}
        </Box>
      )}

      {/* 用户决策 */}
      <Box marginTop={1} flexDirection="column">
        <Text dimColor>
          您可以选择:
        </Text>
        <Box paddingLeft={2}>
          <Text>
            • 按 <Text bold>y</Text> 坚持执行原指令
          </Text>
        </Box>
        <Box paddingLeft={2}>
          <Text>
            • 按 <Text bold>n</Text> 采纳我的建议
          </Text>
        </Box>
        <Box paddingLeft={2}>
          <Text>
            • 输入新指令重新描述您的需求
          </Text>
        </Box>
      </Box>
    </Box>
  );
}
