import React, { useEffect, useMemo } from 'react';
import { Box, useApp, useInput } from 'ink';
import { useStore } from '@nanostores/react';
import type { GatewayClient, GatewayEvent } from './gatewayClient.js';
import Branding from './components/branding.js';
import ContentRegion from './components/contentRegion.js';
import ErrorBoundary from './components/errorBoundary.js';
import InputRegion from './components/inputRegion.js';
import Overlays from './components/overlays.js';
import { transcriptAtom, streamingAtom, thinkingAtom } from './stores/transcriptStore.js';
import { toolsAtom } from './stores/runtimeStore.js';
import { overlayAtom, closeOverlay } from './stores/overlayStore.js';
import { sessionInfoAtom, busyAtom, statusAtom } from './stores/sessionStore.js';
import { inputBufferAtom, inputAtom, scrollOffsetAtom, completionItemsAtom, completionIndexAtom } from './stores/inputStore.js';
import { routeEvent } from './stores/eventRouter.js';
import { submitPrompt, answerOverlay, requestCompletion, drainQueue } from './handlers/promptHandler.js';
import { TIMEOUTS, SCROLL_CONFIG } from './constants.js';

interface Props {
  gateway: GatewayClient;
}

export default function App({ gateway }: Props) {
  const app = useApp();
  const overlay = useStore(overlayAtom);

  // Ink useInput 处理特殊键
  useInput((input, key) => {
    // Ctrl+C
    if (key.ctrl && input === 'c') {
      if (overlayAtom.get().type !== 'none') {
        closeOverlay();
      } else if (busyAtom.get()) {
        void gateway.request('session.interrupt', {
          session_id: sessionInfoAtom.get()?.id,
        });
        busyAtom.set(false);
        statusAtom.set('interrupted');
      } else if (inputAtom.get()) {
        inputAtom.set('');
      } else {
        gateway.stop();
        app.exit();
      }
      return;
    }

    // Ctrl+D
    if (key.ctrl && input === 'd') {
      gateway.stop();
      app.exit();
      return;
    }

    // 滚动
    const hasCompletions = completionItemsAtom.get().length > 0;
    if (!hasCompletions && (key.upArrow || key.downArrow || key.pageUp || key.pageDown)) {
      const state = {
        offset: scrollOffsetAtom.get(),
        max: transcriptAtom.get().length,
      };
      let newOffset = state.offset;
      if (key.pageUp) newOffset = Math.min(state.max - 1, state.offset + SCROLL_CONFIG.PAGE);
      else if (key.pageDown) newOffset = Math.max(0, state.offset - SCROLL_CONFIG.PAGE);
      else if (key.upArrow) newOffset = Math.min(state.max - 1, state.offset + SCROLL_CONFIG.STEP);
      else if (key.downArrow) newOffset = Math.max(0, state.offset - SCROLL_CONFIG.STEP);
      scrollOffsetAtom.set(newOffset);
    }
  }, { isActive: true });

  useEffect(() => {
    const onEvent = (event: GatewayEvent) => {
      routeEvent(event);

      if (event.type === 'message.complete') {
        setTimeout(() => drainQueue(gateway), 0);
      }
    };

    gateway.on('event', onEvent);
    return () => {
      gateway.off('event', onEvent);
    };
  }, [gateway]);

  useEffect(() => {
    let sessionCreated = false;
    
    const existingSessionId = sessionInfoAtom.get()?.id;
    
    if (existingSessionId) {
      void gateway.request<{ info?: import('./types.js').SessionInfo }>('session.resume', {
        session_id: existingSessionId,
        cols: process.stdout.columns || 80
      })
        .then(result => {
          if (sessionCreated) return;
          sessionCreated = true;
          
          if (result.info) {
            sessionInfoAtom.set(result.info);
          }
          
          if (statusAtom.get() === 'starting') {
            statusAtom.set('ready');
          }
        })
        .catch(() => {
          if (sessionCreated) return;
          sessionCreated = true;
          
          void gateway.request<{
            session_id: string;
            info?: import('./types.js').SessionInfo
          }>('session.create', {
            cols: process.stdout.columns || 80
          })
            .then(result => {
              sessionInfoAtom.set(result.info || { id: result.session_id });
              if (statusAtom.get() === 'starting') {
                statusAtom.set('ready');
              }
            });
        });
    } else {
      void gateway.request<{
        session_id: string;
        info?: import('./types.js').SessionInfo
      }>('session.create', {
        cols: process.stdout.columns || 80
      })
        .then(result => {
          if (sessionCreated) return;
          sessionCreated = true;
          
          sessionInfoAtom.set(result.info || { id: result.session_id });

          if (statusAtom.get() === 'starting') {
            statusAtom.set('ready');
          }
        })
        .catch(error => {
          if (sessionCreated) return;
          sessionCreated = true;
          
          const msg = error instanceof Error ? error.message : String(error);
          import('./stores/transcriptStore.js').then(m =>
            m.appendTranscript({
              id: `${Date.now()}:e`,
              role: 'system',
              text: msg,
              timestamp: Date.now()
            })
          );
        });
    }
  }, [gateway]);

  useEffect(() => {
    const timer = setTimeout(
      () => void requestCompletion(inputBufferAtom.get().join('\n'), gateway),
      TIMEOUTS.COMPLETION_REQUEST
    );
    return () => clearTimeout(timer);
  }, [gateway]);

  useEffect(() => {
    const unsub = inputBufferAtom.listen(() => {
      void requestCompletion(inputBufferAtom.get().join('\n'), gateway);
    });
    return unsub;
  }, [gateway]);

  useEffect(() => {
    if (overlay.type !== 'approval') return;

    const timeoutRemaining = overlay.timeout_remaining ?? TIMEOUTS.APPROVAL;

    if (timeoutRemaining <= 0) {
      void answerOverlay(gateway);
      return;
    }

    const timer = setTimeout(() => {
      const ov = overlayAtom.get();

      if (ov.type !== 'approval') return;

      overlayAtom.set({
        ...ov,
        timeout_remaining: Math.max(0, (ov.timeout_remaining ?? TIMEOUTS.APPROVAL) - 1)
      });
    }, 1000);

    return () => clearTimeout(timer);
  }, [gateway, overlay]);

  const transcript = useStore(transcriptAtom);
  const streaming = useStore(streamingAtom);
  const thinking = useStore(thinkingAtom);
  const tools = useStore(toolsAtom);

  const hideBranding = useMemo(
    () => transcript.length === 0 && !streaming && !thinking && tools.length === 0,
    [transcript.length, streaming, thinking, tools.length]
  );

  return (
    <Box flexDirection="column" minHeight={24}>
      {!hideBranding ? <Branding /> : null}
      <ErrorBoundary level="content">
        <ContentRegion />
      </ErrorBoundary>
      <Overlays />
      <InputRegion
        onSubmit={(text) => {
          inputBufferAtom.set([]);
          void submitPrompt(text, gateway);
        }}
      />
    </Box>
  );
}
