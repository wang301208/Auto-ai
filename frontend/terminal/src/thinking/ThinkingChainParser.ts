import type { ThinkingChainData, ThinkingNode } from '../types';

export class ThinkingChainParser {
  parse(data: ThinkingChainData): { nodeMap: Map<string, ThinkingNode>; rootChildren: string[] } {
    const nodeMap = new Map<string, ThinkingNode>();
    const rootChildren: string[] = [];
    const visited = new Set<string>();

    for (const node of data.nodes) {
      nodeMap.set(node.id, node);
    }

    for (const node of data.nodes) {
      if (node.parentId === null) {
        rootChildren.push(node.id);
      } else if (!nodeMap.has(node.parentId)) {
        console.warn(`[ThinkingChainParser] Node ${node.id} has invalid parentId ${node.parentId}`);
      }
    }

    const hasCycle = this.detectCycle(data.rootId, nodeMap, visited);
    if (hasCycle) {
      throw new Error('[ThinkingChainParser] Cycle detected in thinking chain');
    }

    return { nodeMap, rootChildren };
  }

  private detectCycle(
    nodeId: string,
    nodeMap: Map<string, ThinkingNode>,
    visited: Set<string>,
    recursionStack: Set<string> = new Set()
  ): boolean {
    visited.add(nodeId);
    recursionStack.add(nodeId);

    const node = nodeMap.get(nodeId);
    if (!node) return false;

    const children = Array.from(nodeMap.values()).filter(n => n.parentId === nodeId);
    for (const child of children) {
      if (!visited.has(child.id)) {
        if (this.detectCycle(child.id, nodeMap, visited, recursionStack)) {
          return true;
        }
      } else if (recursionStack.has(child.id)) {
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }
}
