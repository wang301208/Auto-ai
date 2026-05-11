import React from 'react';
import { Box, Text } from 'ink';
import type { OverlayState } from '../types.js';
import { theme } from '../theme.js';

const approvalChoices = ['once', 'session', 'always', 'deny'];
const approvalChoiceLabels: Record<string, string> = {
  once: '本次同意',
  session: '本会话同意',
  always: '始终同意',
  deny: '拒绝'
};

export default function Overlays({ overlay }: { overlay: OverlayState }) {
  if (overlay.type === 'none') return null;

  if (overlay.type === 'approval') {
    const approvalTimeoutRemaining = overlay.timeout_remaining;
    return (
      <Box borderStyle="round" borderColor={theme.warn} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.warn} bold>需要审批</Text>
        <Text>{overlay.command || '操作'}</Text>
        {overlay.description ? <Text color={theme.dim}>{overlay.description}</Text> : null}
        {typeof approvalTimeoutRemaining === 'number' ? (
          <Text color={theme.dim}>{approvalTimeoutRemaining}s 后自动同意，30 秒未操作将自动同意</Text>
        ) : null}
        <Text>
          {approvalChoices.map((choice, index) => `${index === overlay.selected ? '>' : ' '} ${approvalChoiceLabels[choice]}`).join('  ')}
        </Text>
      </Box>
    );
  }

  if (overlay.type === 'clarify') {
    return (
      <Box borderStyle="round" borderColor={theme.prompt} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.prompt} bold>需要补充信息</Text>
        <Text>{overlay.question}</Text>
        {overlay.freeText || !overlay.choices ? (
          <Text color={theme.dim}>输入回答，按 Enter 提交：{overlay.value}</Text>
        ) : (
          overlay.choices.map((choice, index) => (
            <Text color={index === overlay.selected ? theme.prompt : theme.text} key={`${choice}:${index}`}>
              {index === overlay.selected ? '>' : '  '}
              {index + 1}. {choice}
            </Text>
          ))
        )}
      </Box>
    );
  }

  if (overlay.type === 'secret') {
    return (
      <Box borderStyle="round" borderColor={theme.warn} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.warn} bold>密钥输入</Text>
        <Text>{overlay.prompt}</Text>
        <Text color={theme.dim}>{overlay.env_var}: {'*'.repeat(overlay.value.length)}</Text>
      </Box>
    );
  }

  if (overlay.type === 'sudo') {
    return (
      <Box borderStyle="round" borderColor={theme.warn} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.warn} bold>Sudo 密码</Text>
        <Text color={theme.dim}>{'*'.repeat(overlay.value.length)}</Text>
      </Box>
    );
  }

  if (overlay.type === 'sessionPicker') {
    return (
      <Box borderStyle="round" borderColor={theme.prompt} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.prompt} bold>恢复会话</Text>
        {overlay.sessions.map((session, index) => (
          <Text color={index === overlay.selected ? theme.prompt : theme.text} key={session.id}>
            {index === overlay.selected ? '>' : '  '}
            {session.title} <Text color={theme.dim}>({session.message_count || 0}) {session.preview || ''}</Text>
          </Text>
        ))}
      </Box>
    );
  }

  if (overlay.type === 'modelPicker') {
    return (
      <Box borderStyle="round" borderColor={theme.prompt} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.prompt} bold>选择模型</Text>
        {overlay.providers.map((provider, index) => (
          <Text color={index === overlay.selected ? theme.prompt : theme.text} key={provider.slug}>
            {index === overlay.selected ? '>' : '  '}
            {provider.name} <Text color={theme.dim}>{(provider.models || []).join(', ')}</Text>
          </Text>
        ))}
      </Box>
    );
  }

  if (overlay.type === 'modelSetup') {
    const labels: Record<typeof overlay.step, string> = {
      base_url: '接口地址',
      api_key_env: '密钥环境变量',
      api_key: 'API 密钥',
      model: '模型型号'
    };
    return (
      <Box borderStyle="round" borderColor={theme.prompt} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.prompt} bold>自定义模型配置</Text>
        <Text color={theme.dim}>{overlay.provider.name}</Text>
        <Text>{labels[overlay.step]}：{overlay.step === 'api_key' && overlay.value ? '*'.repeat(overlay.value.length) : overlay.value}</Text>
        <Text color={theme.dim}>按 Enter 确认，Esc 取消</Text>
      </Box>
    );
  }

  return null;
}

export { approvalChoices };


