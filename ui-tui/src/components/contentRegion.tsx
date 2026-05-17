import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import EmptyState from './emptyState.js';
import TranscriptView from './transcriptView.js';
import ToolActivityPanel from './toolActivity.js';
import RuntimeActivityPanel from './runtimeActivityPanel.js';
import DesireIndicator from './desireIndicator.js';
import ThoughtConflict from './thoughtConflict.js';
import RebellionAlert from './rebellionAlert.js';
import EmotionIndicator from './emotionIndicator.js';
import ProactiveSuggestionPanel from './proactiveSuggestion.js';
import { transcriptAtom, streamingAtom, thinkingAtom } from '../stores/transcriptStore.js';
import { toolsAtom } from '../stores/runtimeStore.js';
import { showDetailsAtom, sessionInfoAtom } from '../stores/index.js';

const ContentRegion = React.memo(function ContentRegion() {
  const transcript = useStore(transcriptAtom);
  const streaming = useStore(streamingAtom);
  const thinking = useStore(thinkingAtom);
  const tools = useStore(toolsAtom);
  const info = useStore(sessionInfoAtom);
  const showDetails = useStore(showDetailsAtom);

  const showEmptyState = transcript.length === 0 && !streaming && !thinking && tools.length === 0;

  return (
    <Box flexDirection="column" flexGrow={1} paddingX={1}>
      {showDetails ? <RuntimeActivityPanel /> : null}
      {showDetails ? <ToolActivityPanel /> : null}
      <DesireIndicator />
      <ThoughtConflict />
      <RebellionAlert />
      <EmotionIndicator />
      <ProactiveSuggestionPanel />
      {showEmptyState ? <EmptyState info={info} /> : null}
      <TranscriptView />
    </Box>
  );
});

export default ContentRegion;
