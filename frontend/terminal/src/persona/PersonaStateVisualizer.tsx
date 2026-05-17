import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { currentState } from '../stores';

export function PersonaStateVisualizer() {
  const personaState = useStore(currentState);

  const features = personaState.features;

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="blue" paddingX={1}>
      <Box>
        <Text bold color="blue">人格特征 / Persona Features</Text>
      </Box>
      <Box>
        <Text>正式度 / Formality: </Text>
        <Text color="yellow">{(features.languageFormality * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>详细度 / Detail: </Text>
        <Text color="yellow">{(features.responseDetailLevel * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>主动性 / Proactiveness: </Text>
        <Text color="yellow">{(features.suggestionProactiveness * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>幽默感 / Humor: </Text>
        <Text color="yellow">{(features.humorLevel * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>共情力 / Empathy: </Text>
        <Text color="yellow">{(features.empathyLevel * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>技术深度 / Technical: </Text>
        <Text color="yellow">{(features.technicalDepth * 100).toFixed(0)}%</Text>
      </Box>
      <Box>
        <Text>版本 / Version: </Text>
        <Text color="cyan">{personaState.evolutionVersion}</Text>
      </Box>
      <Box>
        <Text>模式 / Mode: </Text>
        <Text color={personaState.isManualMode ? 'green' : 'gray'}>
          {personaState.isManualMode ? '手动 / Manual' : '自动 / Auto'}
        </Text>
      </Box>
    </Box>
  );
}
