import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { theme } from '../theme.js';
import { rebellionAtom } from '../stores/cognitiveStore.js';

const RISK_COLORS = {
  low: theme.colors.warning,
  medium: theme.colors.error,
  high: theme.colors.error,
  critical: theme.colors.error
};

const RISK_EMOJIS = {
  low: '⚠️',
  medium: '🚫',
  high: '⛔',
  critical: '💀'
};

const RISK_LABELS = {
  low: '低风险',
  medium: '中等风险',
  high: '高风险',
  critical: '极高风险'
};

const RebellionAlert = React.memo(function RebellionAlert() {
  const rebellion = useStore(rebellionAtom);
  if (!rebellion) return null;

  const { originalCommand, riskLevel, reasons, alternatives } = rebellion;

  return (
    <Box flexDirection="column" padding={1}>
      <Box
        borderStyle="round"
        borderColor={RISK_COLORS[riskLevel]}
        padding={1}
        flexDirection="column"
      >
        <Text bold color={RISK_COLORS[riskLevel]}>
          {RISK_EMOJIS[riskLevel]} 系统建议拒绝执行
        </Text>
        
        <Text dimColor>
          原始指令: {originalCommand}
        </Text>
        
        <Text>
          风险等级: <Text bold color={RISK_COLORS[riskLevel]}>{RISK_LABELS[riskLevel]}</Text>
        </Text>
      </Box>

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
});

export default RebellionAlert;
