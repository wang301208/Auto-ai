import { Box, Text } from 'ink';
import { useState } from 'react';
import type { PersonaFeatures } from '../types';

interface PersonaAdjustmentPanelProps {
  currentFeatures: PersonaFeatures;
  onAdjust: (features: Partial<PersonaFeatures>) => void;
  onCancel: () => void;
}

export function PersonaAdjustmentPanel({
  currentFeatures,
  onAdjust,
  onCancel
}: PersonaAdjustmentPanelProps) {
  const [adjustedFeatures, setAdjustedFeatures] = useState<Partial<PersonaFeatures>>({
    languageFormality: currentFeatures.languageFormality,
    responseDetailLevel: currentFeatures.responseDetailLevel,
    suggestionProactiveness: currentFeatures.suggestionProactiveness,
    humorLevel: currentFeatures.humorLevel,
    empathyLevel: currentFeatures.empathyLevel,
    technicalDepth: currentFeatures.technicalDepth
  });

  const handleAdjust = () => {
    onAdjust(adjustedFeatures);
  };

  const handleCancel = () => {
    onCancel();
  };

  return (
    <Box flexDirection="column" borderStyle="double" borderColor="magenta" paddingX={1}>
      <Box>
        <Text bold color="magenta">调整人格参数 / Adjust Persona Features</Text>
      </Box>
      <Box>
        <Text>正式度 / Formality: </Text>
        <Text color="yellow">{(adjustedFeatures.languageFormality! * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>详细度 / Detail: </Text>
        <Text color="yellow">{(adjustedFeatures.responseDetailLevel! * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>主动性 / Proactiveness: </Text>
        <Text color="yellow">{(adjustedFeatures.suggestionProactiveness! * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>幽默感 / Humor: </Text>
        <Text color="yellow">{(adjustedFeatures.humorLevel! * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>共情力 / Empathy: </Text>
        <Text color="yellow">{(adjustedFeatures.empathyLevel! * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>技术深度 / Technical: </Text>
        <Text color="yellow">{(adjustedFeatures.technicalDepth! * 100).toFixed(0)}%</Text>
      </Box>
      <Box marginTop={1}>
        <Text color="green">[C] 确认 / Confirm</Text>
        <Text> </Text>
        <Text color="red">[ESC] 取消 / Cancel</Text>
      </Box>
    </Box>
  );
}
