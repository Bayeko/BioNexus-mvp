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
    // Register cron jobs for all enabled cron-triggered workflows
    for (const workflow of this.workflowRegistry.listEnabled()) {
      if (workflow.trigger.type === 'cron' && workflow.trigger.cron) {
        const task = cron.schedule(workflow.trigger.cron, () => {
          console.log(JSON.stringify({
            timestamp: new Date().toISOString(),
            level: 'info',
            message: `Cron triggered: ${workflow.name}`,
          }));
          this.eventBus.emit('workflow:trigger', { type: workflow.id });
        });
        this.tasks.push(task);
      }
    }

    // GitHub polling for event-driven workflows
    const pollMs = this.config.githubPollIntervalMinutes * 60 * 1000;
    const githubInterval = setInterval(() => {
      this.eventBus.emit('workflow:trigger', { type: 'builtin-cross-agent-sync' });
    }, pollMs);
    this.intervals.push(githubInterval);

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: `Scheduler started: ${this.tasks.length} cron jobs, GitHub poll every ${this.config.githubPollIntervalMinutes}m`,
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
