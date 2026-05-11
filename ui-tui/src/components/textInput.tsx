import React from 'react';
import {Text} from 'ink';
import InkTextInput from 'ink-text-input';
import {theme} from '../theme.js';

interface Props {
  disabled?: boolean;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  onHistoryNext?: () => void;
  onHistoryPrevious?: () => void;
  onSubmit: (value: string) => void;
}

function mouseWheelDirection(data: string): 'up' | 'down' | null {
  if (/\x1B\[<64;\d+;\d+[mM]/.test(data) || /\x1B\[M`/.test(data)) return 'up';
  if (/\x1B\[<65;\d+;\d+[mM]/.test(data) || /\x1B\[Ma/.test(data)) return 'down';
  return null;
}

function containsTerminalMouseEvent(data: string) {
  return /\x1B\[(?:<\d+;\d+;\d+[mM]|M[\s\S]{3})/.test(data);
}

function isWheelOverInputArea(data: string) {
  const match = /\x1B\[<(?:64|65);(?<x>\d+);(?<y>\d+)[mM]/.exec(data);
  if (!match?.groups?.y) return true;

  const terminalRows = process.stdout.rows || 0;
  if (!terminalRows) return true;

  const y = Number.parseInt(match.groups.y, 10);
  return y >= Math.max(1, terminalRows - 4);
}

export default function TextInput({
  disabled = false,
  placeholder,
  value,
  onChange,
  onHistoryNext,
  onHistoryPrevious,
  onSubmit
}: Props) {
  if (disabled) {
    return <Text color={theme.dim}>{placeholder || '等待当前操作完成'}</Text>;
  }

  return (
    <InkTextInput
      focus
      placeholder={placeholder}
      showCursor
      value={value}
      onChange={nextValue => {
        if (!containsTerminalMouseEvent(nextValue)) {
          onChange(nextValue);
          return;
        }

        const direction = mouseWheelDirection(nextValue);
        if (direction && isWheelOverInputArea(nextValue)) {
          if (direction === 'up') onHistoryPrevious?.();
          if (direction === 'down') onHistoryNext?.();
        }
      }}
      onSubmit={() => onSubmit(value)}
    />
  );
}
