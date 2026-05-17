import { selectNode, toggleExpand, setViewMode } from '../stores';

export function selectNodeById(nodeId: string) {
  selectNode(nodeId);
}

export function toggleNodeExpand(nodeId: string) {
  toggleExpand(nodeId);
}

export function changeViewMode(mode: 'tree' | 'timeline' | 'flat') {
  setViewMode(mode);
}

export function getNodePath(nodeId: string): string[] {
  return [nodeId];
}
