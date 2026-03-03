import { EventEmitter } from 'node:events';

export interface WorkflowTriggerEvent {
  type: string;
  payload?: Record<string, unknown>;
}

interface EventMap {
  'workflow:trigger': [WorkflowTriggerEvent];
  'workflow:scan-meetings': [];
  'proposal:created': [{ proposalId: string }];
  'proposal:approved': [{ proposalId: string }];
  'proposal:rejected': [{ proposalId: string }];
}

export class EventBus {
  private emitter = new EventEmitter();

  on<K extends keyof EventMap>(event: K, listener: (...args: EventMap[K]) => void): void {
    this.emitter.on(event, listener as (...args: unknown[]) => void);
  }

  emit<K extends keyof EventMap>(event: K, ...args: EventMap[K]): void {
    this.emitter.emit(event, ...args);
  }

  off<K extends keyof EventMap>(event: K, listener: (...args: EventMap[K]) => void): void {
    this.emitter.off(event, listener as (...args: unknown[]) => void);
  }
}

export function createEventBus(): EventBus {
  return new EventBus();
}
