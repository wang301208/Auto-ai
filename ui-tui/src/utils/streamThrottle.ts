interface StringAtom {
  set: (v: string) => void;
  get: () => string;
}

export class StreamThrottler {
  private lastFlush = 0;
  private pendingText = '';
  private flushTimer: ReturnType<typeof setTimeout> | null = null;
  private throttleMs: number;

  constructor(throttleMs = 16) {
    this.throttleMs = throttleMs;
  }

  append(text: string, atom: StringAtom): void {
    this.pendingText += text;

    const now = Date.now();
    if (now - this.lastFlush >= this.throttleMs) {
      this.flush(atom);
    } else if (!this.flushTimer) {
      this.flushTimer = setTimeout(() => {
        this.flush(atom);
        this.flushTimer = null;
      }, this.throttleMs - (now - this.lastFlush));
    }
  }

  reset(): void {
    this.pendingText = '';
    this.lastFlush = 0;
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
  }

  private flush(atom: StringAtom): void {
    if (!this.pendingText) return;
    atom.set(atom.get() + this.pendingText);
    this.pendingText = '';
    this.lastFlush = Date.now();
  }
}

export const defaultThrottler = new StreamThrottler();

export function throttledStreamAppend(text: string, atom: StringAtom): void {
  defaultThrottler.append(text, atom);
}

export function resetThrottle(): void {
  defaultThrottler.reset();
}
