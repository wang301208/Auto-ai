import React from 'react';
import InkTextInput from 'ink-text-input';
import { theme } from '../theme.js';

interface Props {
  disabled?: boolean;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export default function TextInput({
  disabled = false,
  placeholder,
  value,
  onChange,
  onSubmit
}: Props) {
  if (disabled) {
    return <InkTextInput value={value} onChange={() => {}} onSubmit={() => {}} placeholder={placeholder} showCursor={false} />;
  }

  return (
    <InkTextInput
      focus
      placeholder={placeholder}
      showCursor
      value={value}
      onChange={onChange}
      onSubmit={onSubmit}
    />
  );
}
