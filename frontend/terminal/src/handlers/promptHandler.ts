import { gatewayClient } from '../client/gateway';
import { updateChain } from '../stores/transcriptStore';
import type { ThoughtChain, ThinkingChainData, ThinkingNode } from '../types';
import { ThinkingNodeType, ThinkingNodeState } from '../types';

function convertThoughtChainToData(chain: ThoughtChain): ThinkingChainData {
  const nodes: Map<string, ThinkingNode> = new Map();
  let rootId: string = '';

  function convertNode(node: ThoughtChain['root'], parentId: string | null = null): string {
    const id = `thought_${node.id}`;

    nodes.set(id, {
      id,
      content: { zh: node.description },
      type: ThinkingNodeType.ANALYSIS,
      state: node.status === 'completed' ? ThinkingNodeState.COMPLETED : node.status === 'processing' ? ThinkingNodeState.PROCESSING : ThinkingNodeState.PENDING,
      parentId,
      timestamp: node.start_time ? new Date(node.start_time).toISOString() : new Date().toISOString(),
      metadata: {
        confidence: node.confidence,
        level: node.level
      }
    });

    if (node.children && node.children.length > 0) {
      node.children.forEach(child => {
        convertNode(child, id);
      });
    }

    return id;
  }

  rootId = convertNode(chain.root, null);

  return {
    sessionId: '',
    nodes: Array.from(nodes.values()),
    rootId,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
}

export async function registerPromptHandler() {
  try {
    await gatewayClient.request('runtime.subscribe_events', {
      event_types: ['thought']
    });
  } catch (error) {
    console.error('[PromptHandler] Failed to subscribe to thought events:', error);
  }
}
