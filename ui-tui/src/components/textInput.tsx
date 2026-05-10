import React from 'react';
import { Text } from 'ink';
import InkTextInput from 'ink-text-input';
import { theme } from '../theme.js';

interface Props {
  disabled?: boolean;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
}

export default function TextInput({ disabled = false, placeholder, value, onChange, onSubmit }: Props) {
  if (disabled) {
    return <Text color={theme.dim}>{placeholder || '等待当前操作完成'}</Text>;
  }

  return (
    <InkTextInput
      focus
      placeholder={placeholder}
      showCursor
      value={value}
      onChange={onChange}
      onSubmit={() => onSubmit(value)}
    />
  );
}


