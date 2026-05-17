import { Box, Text } from 'ink';
import TextInput from 'ink-text-input';
import { useState } from 'react';
import { useInput } from 'ink';
import { eventBus } from '../client/eventBus';

export function InputRegion() {
  const [value, setValue] = useState('');

  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      process.exit(0);
    }

    if (key.ctrl && input === 'l') {
      eventBus.emit('language.switch', 'bilingual');
    }
  });

  const handleSubmit = () => {
    if (value.trim()) {
      eventBus.emit('user.input', value);
      setValue('');
    }
  };

  return (
    <Box borderStyle="single" borderColor="gray" paddingX={1}>
      <Text color="green">❯ </Text>
      <TextInput
        value={value}
        onChange={setValue}
        onSubmit={handleSubmit}
        placeholder="输入消息... / Type a message..."
      />
    </Box>
  );
}
