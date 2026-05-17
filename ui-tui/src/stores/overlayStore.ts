import { atom } from 'nanostores';
import type { OverlayState } from '../types.js';

export const overlayAtom = atom<OverlayState>({ type: 'none' });

export function closeOverlay(): void {
  overlayAtom.set({ type: 'none' });
}

export function isOverlayOpen(): boolean {
  return overlayAtom.get().type !== 'none';
}
