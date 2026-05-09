import React from 'react';
import { Box, Text } from 'ink';
import type { SessionInfo } from '../types.js';
import { glyph, theme } from '../theme.js';

function toolCount(info?: SessionInfo | null) {
  return info?.tools
    ? Object.values(info.tools).reduce((sum: number, items: string[]) => sum + items.length, 0)
    : 0;
}

const asciiArt = [
  '    /\\',
  '   /  \\',
  '  / /\\ \\',
  ' / ____ \\',
  '/_/    \\_\\',
  '  LOCAL',
  '  AGENT'
];

export default function EmptyState({ info }: { info?: SessionInfo | null }) {
  const tools = toolCount(info);
  const cwd = info?.cwd || process.cwd();
  const model = info?.model || 'local-runtime';

  return (
    <Box flexDirection="column" paddingTop={1}>
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color={theme.assistant}>
          {glyph.assistant} LOCAL AGENT
        </Text>
        <Text color={theme.dim}>Autonomous Runtime Terminal</Text>
      </Box>

      <Box borderColor={theme.border} borderStyle="round" flexDirection="row" paddingX={2} paddingY={1}>
        <Box flexDirection="column" marginRight={3} width={14}>
          {asciiArt.map((line, index) => (
            <Text color={index < 5 ? theme.assistant : theme.dim} key={`${index}:${line}`}>
              {line}
            </Text>
          ))}
          <Text />
          <Text color={theme.dim} wrap="truncate-end">
            {model}
          </Text>
          <Text color={theme.dim} wrap="truncate-end">
            {cwd}
          </Text>
        </Box>

        <Box flexDirection="column" width={58}>
          <Box justifyContent="center" marginBottom={1}>
            <Text bold color={theme.assistant}>
              Command Center {info?.version ? `v${info.version}` : ''}
            </Text>
          </Box>

          <Box flexDirection="column">
            <Text bold color={theme.prompt}>
              {glyph.cursor} Available Tools
            </Text>
            <Text color={theme.text} wrap="truncate">
              runtime: {tools || 0} tools loaded
            </Text>
            <Text color={theme.dim} wrap="truncate">
              local runtime ready
            </Text>
          </Box>

          <Box flexDirection="column" marginTop={1}>
            <Text bold color={theme.prompt}>
              {glyph.cursor} Core Commands
            </Text>
          <Text color={theme.text} wrap="truncate">
            /status, /health, /preflight, /host, /tools, /approvals
          </Text>
          <Text color={theme.dim} wrap="truncate">
            /messaging, /blueprints, /skills, /algorithms, /audits
          </Text>
          <Text color={theme.dim} wrap="truncate">
            !cmd runs shell | @path attaches project context
          </Text>
          </Box>

          <Box flexDirection="column" marginTop={1}>
            <Text bold color={theme.prompt}>
              {glyph.cursor} System
            </Text>
            <Text color={theme.text} wrap="truncate">
              TUI process → Python gateway subprocess → stdin/stdout JSON-RPC
            </Text>
            <Text color={theme.dim} wrap="truncate">
              direct child process transport
            </Text>
          </Box>

          <Text />

          <Text color={theme.text}>
            {tools || 0} tools | local runtime | <Text color={theme.dim}>/help for commands</Text>
          </Text>
        </Box>
      </Box>
    </Box>
  );
}
