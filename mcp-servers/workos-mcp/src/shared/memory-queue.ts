/**
 * Memory Queue - Write task completion events to queue for Memory V2 processing.
 *
 * This writes task completion events to a JSONL file that the Python
 * workos_memory_bridge daemon picks up and stores in Memory V2.
 *
 * Architecture:
 * 1. TypeScript (this file) writes events to JSONL queue file
 * 2. Python daemon reads queue, stores in Memory V2 (Neon pgvector)
 * 3. Queue file is archived after processing
 *
 * Why JSONL queue?
 * - Non-blocking: TypeScript doesn't wait for Python
 * - Resilient: Events survive process restarts
 * - Simple: No need for HTTP server or message broker
 * - Atomic: Each line is a complete event
 */

import { appendFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

// Queue file location - matches Python bridge
const QUEUE_DIR = process.env.THANOS_STATE_DIR || "/Users/jeremy/Projects/Thanos/State";
const QUEUE_FILE = `${QUEUE_DIR}/workos_memory_queue.jsonl`;

/**
 * Task completion event data structure.
 */
export interface TaskCompletionEvent {
  id: number;
  title: string;
  description?: string | null;
  clientId?: number | null;
  clientName?: string | null;
  valueTier?: string | null;
  drainType?: string | null;
  cognitiveLoad?: string | null;
  pointsFinal?: number | null;
  completedAt?: Date | string | null;
  project?: string | null;
}

/**
 * Decision event data structure.
 */
export interface DecisionEvent {
  decision: string;
  task_id?: number;
  client_name?: string;
  alternatives?: string[];
  rationale?: string;
}

/**
 * Queue event wrapper.
 */
interface QueueEvent {
  type: "task_completion" | "decision";
  data: TaskCompletionEvent | DecisionEvent;
  timestamp: string;
}

/**
 * Write an event to the memory queue file.
 *
 * This is a synchronous, non-blocking operation that appends to the queue file.
 * The Python daemon will pick up and process the event.
 *
 * @param eventType - Type of event (task_completion, decision)
 * @param data - Event data
 * @returns true if successfully written, false otherwise
 */
export function writeToMemoryQueue(
  eventType: "task_completion" | "decision",
  data: TaskCompletionEvent | DecisionEvent
): boolean {
  try {
    // Ensure directory exists
    const dir = dirname(QUEUE_FILE);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    // Create event wrapper
    const event: QueueEvent = {
      type: eventType,
      data,
      timestamp: new Date().toISOString(),
    };

    // Append to queue file (synchronous to ensure write completes)
    appendFileSync(QUEUE_FILE, JSON.stringify(event) + "\n");

    return true;
  } catch (error) {
    // Silent failure - don't disrupt task completion
    // Log for debugging but don't throw
    console.error("[MemoryQueue] Failed to write event:", error);
    return false;
  }
}

/**
 * Queue a task completion for memory storage.
 *
 * Call this after a task is successfully completed to capture
 * the context in Memory V2 for later retrieval.
 *
 * @param task - The completed task with all relevant fields
 * @returns true if successfully queued
 */
export function queueTaskCompletion(task: TaskCompletionEvent): boolean {
  return writeToMemoryQueue("task_completion", task);
}

/**
 * Queue a decision for memory storage.
 *
 * Call this when a significant decision is made during task execution.
 * Decisions are stored with higher importance for future reference.
 *
 * @param decision - The decision that was made
 * @param options - Optional metadata about the decision
 * @returns true if successfully queued
 */
export function queueDecision(
  decision: string,
  options?: {
    taskId?: number;
    clientName?: string;
    alternatives?: string[];
    rationale?: string;
  }
): boolean {
  return writeToMemoryQueue("decision", {
    decision,
    task_id: options?.taskId,
    client_name: options?.clientName,
    alternatives: options?.alternatives,
    rationale: options?.rationale,
  });
}
