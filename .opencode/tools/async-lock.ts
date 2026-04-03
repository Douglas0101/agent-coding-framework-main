/**
 * async-lock.ts
 *
 * Simple async mutex for protecting concurrent access to in-memory stores.
 * Uses a queue-based approach: only one holder at a time, others wait.
 *
 * This module is pure TypeScript with no external runtime dependencies.
 */

export class AsyncLock {
  private locked = false;
  private queue: Array<() => void> = [];

  /**
   * Acquire the lock. Returns a release function that must be called
   * when the critical section is complete.
   */
  async acquire(): Promise<() => void> {
    if (!this.locked) {
      this.locked = true;
      return () => this.release();
    }

    return new Promise<void>((resolve) => {
      this.queue.push(() => {
        this.locked = true;
        resolve();
      });
    }).then(() => () => this.release());
  }

  private release(): void {
    if (this.queue.length > 0) {
      const next = this.queue.shift()!;
      next();
    } else {
      this.locked = false;
    }
  }

  /**
   * Check if the lock is currently held.
   */
  get isLocked(): boolean {
    return this.locked;
  }

  /**
   * Get the number of waiters in the queue.
   */
  get queueLength(): number {
    return this.queue.length;
  }
}

/**
 * ReadWriteLock: allows multiple concurrent readers OR a single writer.
 * Writers have priority to prevent writer starvation.
 */
export class ReadWriteLock {
  private readers = 0;
  private writerWaiting = false;
  private writerActive = false;
  private readerQueue: Array<() => void> = [];
  private writerQueue: Array<() => void> = [];

  async acquireRead(): Promise<() => void> {
    if (!this.writerActive && !this.writerWaiting && this.readers === 0) {
      this.readers++;
      return () => this.releaseRead();
    }

    if (!this.writerActive && !this.writerWaiting) {
      this.readers++;
      return () => this.releaseRead();
    }

    return new Promise<void>((resolve) => {
      this.readerQueue.push(() => {
        this.readers++;
        resolve();
      });
      this.processQueues();
    }).then(() => () => this.releaseRead());
  }

  async acquireWrite(): Promise<() => void> {
    return new Promise<void>((resolve) => {
      this.writerWaiting = true;
      this.writerQueue.push(() => {
        this.writerWaiting = false;
        this.writerActive = true;
        resolve();
      });
      this.processQueues();
    }).then(() => () => this.releaseWrite());
  }

  private releaseRead(): void {
    this.readers--;
    if (this.readers === 0) {
      this.processQueues();
    }
  }

  private releaseWrite(): void {
    this.writerActive = false;
    this.processQueues();
  }

  private processQueues(): void {
    if (this.writerActive || this.readers > 0) {
      return;
    }

    if (this.writerQueue.length > 0) {
      const next = this.writerQueue.shift()!;
      next();
    } else {
      while (this.readerQueue.length > 0) {
        const next = this.readerQueue.shift()!;
        next();
      }
    }
  }

  get hasActiveWriter(): boolean {
    return this.writerActive;
  }

  get activeReaders(): number {
    return this.readers;
  }
}
