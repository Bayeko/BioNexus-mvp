import cron from 'node-cron';
import type { EventBus } from './event-bus.js';
import type { WorkflowRegistry } from '../workflows/registry.js';
import type { SchedulerConfig } from '../config.js';

export class Scheduler {
  private tasks: cron.ScheduledTask[] = [];
  private intervals: ReturnType<typeof setInterval>[] = [];

  constructor(
    private config: SchedulerConfig,
    private eventBus: EventBus,
    private workflowRegistry: WorkflowRegistry,
  ) {}

  start(): void {
    // All automatic triggers disabled — workflows are manual-trigger only.
    // Use POST /api/workflows/:id/trigger to run workflows on demand.
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: 'Scheduler started: all automatic triggers disabled (manual-trigger only)',
    }));
  }

  stop(): void {
    for (const task of this.tasks) {
      task.stop();
    }
    for (const interval of this.intervals) {
      clearInterval(interval);
    }
    this.tasks = [];
    this.intervals = [];
  }
}

export function createScheduler(
  config: SchedulerConfig,
  eventBus: EventBus,
  workflowRegistry: WorkflowRegistry,
): Scheduler {
  return new Scheduler(config, eventBus, workflowRegistry);
}
