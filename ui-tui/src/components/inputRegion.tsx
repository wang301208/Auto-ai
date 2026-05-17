import React, { useMemo } from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import TextInput from './textInput.js';
import CompletionList from './completionList.js';
import QueuedMessages from './queuedMessages.js';
import StatusBar from './statusBar.js';
import { theme } from '../theme.js';
import { inputAtom, inputBufferAtom, queueAtom, completionItemsAtom, completionIndexAtom } from '../stores/index.js';
import { overlayAtom } from '../stores/overlayStore.js';
import { busyAtom } from '../stores/sessionStore.js';
import { applyCompletionText } from '../handlers/promptHandler.js';

interface Props {
  onSubmit: (text: string) => void;
}

const InputRegion = React.memo(function InputRegion({ onSubmit }: Props) {
  const input = useStore(inputAtom);
  const inputBuffer = useStore(inputBufferAtom);
  const queue = useStore(queueAtom);
  const completionItems = useStore(completionItemsAtom);
  const completionIndex = useStore(completionIndexAtom);
  const overlay = useStore(overlayAtom);
  const busy = useStore(busyAtom);
  const overlayOpen = overlay.type !== 'none';

  const composedInput = useMemo(
    () => inputBuffer.length ? `${inputBuffer.join('\n')}\n${input}` : input,
    [inputBuffer, input]
  );

  return (
    <Box flexDirection="column" flexShrink={0} paddingX={1}>
      <QueuedMessages items={queue} />
      <CompletionList active={completionIndex} items={completionItems} />

      {inputBuffer.map((line, index) => (
        <Text color={theme.colors.dim} key={`${index}:${line}`}>
          {' '.repeat(2)}{line}
        </Text>
      ))}

      <Box>
        <Text color={input.startsWith('!') ? theme.colors.warning : theme.colors.prompt} bold>
          {input.startsWith('!') ? '$' : '>'}{' '}
        </Text>
        <TextInput
          disabled={overlayOpen}
          placeholder={busy ? 'Ctrl+C 中断当前操作...' : '输入消息或 /help'}
          value={input}
          onChange={v => inputAtom.set(v)}
          onSubmit={() => {
            if (completionItems.length) {
              const item = completionItems[completionIndex];
              if (item) { 
                onSubmit(applyCompletionText(input, item.text)); 
                return; 
              }
            }
            onSubmit(composedInput);
          }}
        />
      </Box>

      <StatusBar />
    </Box>
  );
});

export default InputRegion;
