import { atom, map } from 'nanostores';
import type {
  ThinkingChainData,
  ThinkingNode
} from '../types';

type ViewMode = 'tree' | 'timeline' | 'flat';

export const currentChain = atom<ThinkingChainData | null>(null);
export const selectedNodeId = atom<string | null>(null);
export const expandedNodeIds = map<Set<string>>(new Set());
export const viewMode = atom<ViewMode>('tree');

export function updateChain(data: ThinkingChainData) {
  currentChain.set(data);
}

export function selectNode(nodeId: string | null) {
  selectedNodeId.set(nodeId);
}

export function toggleExpand(nodeId: string) {
  const expanded = expandedNodeIds.get();
  const newExpanded = new Set(expanded);
  if (newExpanded.has(nodeId)) {
    newExpanded.delete(nodeId);
  } else {
    newExpanded.add(nodeId);
  }
  expandedNodeIds.set(newExpanded);
}

export function setViewMode(mode: ViewMode) {
  viewMode.set(mode);
}
