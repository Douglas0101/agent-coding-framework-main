/**
 * DeepAgentMetrics — In-memory metrics collection for the Deep Agent Coding Package.
 *
 * Implements the DeepAgentMetrics interface from execucao.md Section 6.3.
 * Designed for local-first observability; can be extended to Prometheus export.
 *
 * Usage:
 *   import { metrics } from "../lib/metrics"
 *   metrics.recordCommandLatency("bash", 150)
 *   metrics.incrementPathTraversalAttempts()
 *   const snapshot = metrics.snapshot()
 */

// === Metric Types ===

interface HistogramData {
  count: number
  sum: number
  min: number
  max: number
  buckets: Map<string, number> // label -> count
}

interface GaugeData {
  value: number
  lastUpdated: number
}

interface CounterData {
  value: number
}

// === Histogram Helper ===

function createHistogram(): HistogramData {
  return {
    count: 0,
    sum: 0,
    min: Infinity,
    max: -Infinity,
    buckets: new Map(),
  }
}

function observeHistogram(h: HistogramData, value: number, label?: string): void {
  h.count++
  h.sum += value
  if (value < h.min) h.min = value
  if (value > h.max) h.max = value
  if (label) {
    h.buckets.set(label, (h.buckets.get(label) ?? 0) + 1)
  }
}

function histogramAvg(h: HistogramData): number {
  return h.count > 0 ? h.sum / h.count : 0
}

// === DeepAgentMetrics Class ===

class DeepAgentMetrics {
  // Performance (Histogram)
  private commandLatency = createHistogram()
  private filterProcessingTime = createHistogram()

  // Quality (Gauge)
  private jsonPreservationSuccesses = 0
  private jsonPreservationTotal = 0
  private secretRedactionHits = 0
  private secretRedactionTotal = 0

  // Security (Counter)
  private pathTraversalAttempts = 0
  private unauthorizedWriteAttempts = 0
  private doomLoopDenials = 0

  // Operation (Gauge/Counter)
  private commandSuccessCount = 0
  private commandTotalCount = 0
  private agentDispatchErrors = 0

  // === Recording Methods ===

  recordCommandLatency(tool: string, ms: number): void {
    observeHistogram(this.commandLatency, ms, tool)
  }

  recordFilterProcessingTime(ms: number): void {
    observeHistogram(this.filterProcessingTime, ms)
  }

  recordJsonPreservation(success: boolean): void {
    this.jsonPreservationTotal++
    if (success) this.jsonPreservationSuccesses++
  }

  recordSecretRedaction(secretsFound: number): void {
    this.secretRedactionTotal++
    if (secretsFound > 0) this.secretRedactionHits++
  }

  incrementPathTraversalAttempts(): void {
    this.pathTraversalAttempts++
  }

  incrementUnauthorizedWriteAttempts(): void {
    this.unauthorizedWriteAttempts++
  }

  incrementDoomLoopDenials(): void {
    this.doomLoopDenials++
  }

  recordCommandResult(success: boolean): void {
    this.commandTotalCount++
    if (success) this.commandSuccessCount++
  }

  incrementAgentDispatchErrors(): void {
    this.agentDispatchErrors++
  }

  // === Snapshot (for export/logging) ===

  snapshot(): DeepAgentMetricsSnapshot {
    return {
      performance: {
        commandLatencyMs: {
          count: this.commandLatency.count,
          avg: histogramAvg(this.commandLatency),
          min: this.commandLatency.count > 0 ? this.commandLatency.min : 0,
          max: this.commandLatency.count > 0 ? this.commandLatency.max : 0,
          byTool: Object.fromEntries(this.commandLatency.buckets),
        },
        filterProcessingTimeMs: {
          count: this.filterProcessingTime.count,
          avg: histogramAvg(this.filterProcessingTime),
          min: this.filterProcessingTime.count > 0 ? this.filterProcessingTime.min : 0,
          max: this.filterProcessingTime.count > 0 ? this.filterProcessingTime.max : 0,
        },
      },
      quality: {
        jsonPreservationRate: this.jsonPreservationTotal > 0
          ? this.jsonPreservationSuccesses / this.jsonPreservationTotal
          : 0,
        secretRedactionRate: this.secretRedactionTotal > 0
          ? this.secretRedactionHits / this.secretRedactionTotal
          : 0,
      },
      security: {
        pathTraversalAttempts: this.pathTraversalAttempts,
        unauthorizedWriteAttempts: this.unauthorizedWriteAttempts,
        doomLoopDenials: this.doomLoopDenials,
      },
      operation: {
        commandSuccessRate: this.commandTotalCount > 0
          ? this.commandSuccessCount / this.commandTotalCount
          : 0,
        commandTotal: this.commandTotalCount,
        agentDispatchErrors: this.agentDispatchErrors,
      },
    }
  }

  // === Reset (for testing) ===

  reset(): void {
    this.commandLatency = createHistogram()
    this.filterProcessingTime = createHistogram()
    this.jsonPreservationSuccesses = 0
    this.jsonPreservationTotal = 0
    this.secretRedactionHits = 0
    this.secretRedactionTotal = 0
    this.pathTraversalAttempts = 0
    this.unauthorizedWriteAttempts = 0
    this.doomLoopDenials = 0
    this.commandSuccessCount = 0
    this.commandTotalCount = 0
    this.agentDispatchErrors = 0
  }
}

// === Snapshot Type (for serialization) ===

export interface DeepAgentMetricsSnapshot {
  performance: {
    commandLatencyMs: {
      count: number
      avg: number
      min: number
      max: number
      byTool: Record<string, number>
    }
    filterProcessingTimeMs: {
      count: number
      avg: number
      min: number
      max: number
    }
  }
  quality: {
    jsonPreservationRate: number
    secretRedactionRate: number
  }
  security: {
    pathTraversalAttempts: number
    unauthorizedWriteAttempts: number
    doomLoopDenials: number
  }
  operation: {
    commandSuccessRate: number
    commandTotal: number
    agentDispatchErrors: number
  }
}

// === Singleton Export ===

export const metrics = new DeepAgentMetrics()
export type { DeepAgentMetrics }
