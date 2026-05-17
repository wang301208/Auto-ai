import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import MessageLine from './messageLine.js';
import { glyph, theme } from '../theme.js';
import type { TranscriptMessage } from '../types.js';
import { transcriptAtom, streamingAtom, thinkingAtom, scrollOffsetAtom, compactAtom, showDetailsAtom } from '../stores/index.js';
import { VIEWPORT_MESSAGE_LIMIT } from '../constants.js';

export default function TranscriptView() {
  const transcript = useStore(transcriptAtom);
  const streaming = useStore(streamingAtom);
  const thinking = useStore(thinkingAtom);
  const scrollOffset = useStore(scrollOffsetAtom);
  const compact = useStore(compactAtom);
  const showDetails = useStore(showDetailsAtom);

  const streamingMessage: TranscriptMessage | null = streaming
    ? { id: 'streaming', role: 'assistant', text: streaming, timestamp: Date.now() }
    : null;

  // 计算可见窗口
  const transcriptWindowEnd = Math.max(0, transcript.length - scrollOffset);
  const transcriptWindowStart = Math.max(0, transcriptWindowEnd - VIEWPORT_MESSAGE_LIMIT);
  const visibleTranscript = transcript.slice(transcriptWindowStart, transcriptWindowEnd);

  return (
    <>
      {scrollOffset > 0 ? (
        <Text color={theme.colors.dim}>
          已上翻 {scrollOffset} 条消息，PageDown 或向下滚轮返回最新内容
        </Text>
      ) : null}

      {visibleTranscript.map((message, index) => (
        <MessageLine compact={compact} key={message.id} message={message} />
      ))}

      {showDetails && thinking ? (
        <Box marginTop={1} paddingLeft={2}>
          <Text color={theme.colors.dim}>{glyph.thinking} {thinking}</Text>
        </Box>
      ) : null}

      {streamingMessage ? (
        <MessageLine compact={compact} isStreaming message={streamingMessage} />
      ) : null}
    </>
  );
}
