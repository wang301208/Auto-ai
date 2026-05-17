type EventHandler<T = unknown> = (data: T) => void | Promise<void>;

export class EventEmitter {
  private events: Map<string, Set<EventHandler>> = new Map();

  on<T = unknown>(event: string, handler: EventHandler<T>): () => void {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    const handlers = this.events.get(event)!;
    handlers.add(handler as EventHandler);
    
    return () => {
      handlers.delete(handler as EventHandler);
      if (handlers.size === 0) {
        this.events.delete(event);
      }
    };
  }

  off<T = unknown>(event: string, handler: EventHandler<T>): void {
    const handlers = this.events.get(event);
    if (handlers) {
      handlers.delete(handler as EventHandler);
      if (handlers.size === 0) {
        this.events.delete(event);
      }
    }
  }

  emit<T = unknown>(event: string, data?: T): void {
    const handlers = this.events.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          Promise.resolve(handler(data));
        } catch (error) {
          console.error(`[EventEmitter] Error in handler for "${event}":`, error);
        }
      });
    }
  }

  removeAllListeners(event?: string): void {
    if (event) {
      this.events.delete(event);
    } else {
      this.events.clear();
    }
  }
}

export const eventBus = new EventEmitter();
