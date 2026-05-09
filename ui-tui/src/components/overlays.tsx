import React from 'react';
import { Box, Text } from 'ink';
import type { OverlayState } from '../types.js';
import { theme } from '../theme.js';

const approvalChoices = ['once', 'session', 'always', 'deny'];

export default function Overlays({ overlay }: { overlay: OverlayState }) {
  if (overlay.type === 'none') return null;

  if (overlay.type === 'approval') {
    const approvalTimeoutRemaining = overlay.timeout_remaining;
    return (
      <Box borderStyle="round" borderColor={theme.warn} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.warn} bold>Approval required</Text>
        <Text>{overlay.command || 'operation'}</Text>
        {overlay.description ? <Text color={theme.dim}>{overlay.description}</Text> : null}
        {typeof approvalTimeoutRemaining === 'number' ? (
          <Text color={theme.dim}>Auto-approves once in {approvalTimeoutRemaining}s</Text>
        ) : null}
        <Text>
          {approvalChoices.map((choice, index) => `${index === overlay.selected ? '>' : ' '} ${choice}`).join('  ')}
        </Text>
      </Box>
    );
  }

  if (overlay.type === 'clarify') {
    return (
      <Box borderStyle="round" borderColor={theme.prompt} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.prompt} bold>Clarification</Text>
        <Text>{overlay.question}</Text>
        {overlay.freeText || !overlay.choices ? (
          <Text color={theme.dim}>Type answer, Enter to submit: {overlay.value}</Text>
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
        <Text color={theme.warn} bold>Secret input</Text>
        <Text>{overlay.prompt}</Text>
        <Text color={theme.dim}>{overlay.env_var}: {'*'.repeat(overlay.value.length)}</Text>
      </Box>
    );
  }

  if (overlay.type === 'sudo') {
    return (
      <Box borderStyle="round" borderColor={theme.warn} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.warn} bold>Sudo password</Text>
        <Text color={theme.dim}>{'*'.repeat(overlay.value.length)}</Text>
      </Box>
    );
  }

  if (overlay.type === 'sessionPicker') {
    return (
      <Box borderStyle="round" borderColor={theme.prompt} flexDirection="column" paddingX={1} marginTop={1}>
        <Text color={theme.prompt} bold>Resume session</Text>
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
        <Text color={theme.prompt} bold>Model picker</Text>
        {overlay.providers.map((provider, index) => (
          <Text color={index === overlay.selected ? theme.prompt : theme.text} key={provider.slug}>
            {index === overlay.selected ? '>' : '  '}
            {provider.name} <Text color={theme.dim}>{(provider.models || []).join(', ')}</Text>
          </Text>
        ))}
      </Box>
    );
  }

  return null;
}

export { approvalChoices };


