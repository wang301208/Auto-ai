import { Static, Box } from 'ink';
import { SuggestionOverlay } from '../proactive/SuggestionOverlay';
import { NegotiationOverlay } from '../proactive/NegotiationOverlay';

export function Overlays() {
  return (
    <Static items={[
      <SuggestionOverlay key="suggestion" />,
      <NegotiationOverlay key="negotiation" />
    ]}>
      {(item) => (
        <Box width="100%" justifyContent="center">
          {item}
        </Box>
      )}
    </Static>
  );
}
