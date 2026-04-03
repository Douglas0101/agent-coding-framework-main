/**
 * persistence.ts
 *
 * Filesystem-based persistence layer for spec-driven framework stores.
 * Provides save/load operations for registry, linker, checkpoint, and manifest data.
 *
 * This module uses Node.js fs module for file I/O.
 */

import * as fs from 'fs';
import * as path from 'path';
import { AsyncLock } from './async-lock.js';
import { clearBlockedMessage, isClearAllowed } from './clear-guard.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PersistenceConfig {
  base_dir: string;
  auto_save: boolean;
  save_interval_ms: number;
}

export interface PersistenceResult {
  success: boolean;
  errors: string[];
  path?: string;
}

export interface LoadResult<T> {
  success: boolean;
  errors: string[];
  data?: T;
}

// ---------------------------------------------------------------------------
// Default configuration
// ---------------------------------------------------------------------------

const DEFAULT_CONFIG: PersistenceConfig = {
  base_dir: path.join(process.cwd(), '.opencode', 'data'),
  auto_save: false,
  save_interval_ms: 30000,
};

const persistenceLock = new AsyncLock();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function sanitizeFileName(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, '_');
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Saves data to a JSON file in the persistence directory.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function saveData(
  collection: string,
  key: string,
  data: Record<string, unknown>,
  config: Partial<PersistenceConfig> = {},
): Promise<PersistenceResult> {
  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };

  const release = await persistenceLock.acquire();
  try {
    const collectionDir = path.join(effectiveConfig.base_dir, sanitizeFileName(collection));
    ensureDir(collectionDir);

    const filePath = path.join(collectionDir, `${sanitizeFileName(key)}.json`);
    const tempPath = `${filePath}.tmp`;

    // Write to temp file first, then rename (atomic operation on most filesystems)
    fs.writeFileSync(tempPath, JSON.stringify(data, null, 2), 'utf-8');
    fs.renameSync(tempPath, filePath);

    return { success: true, errors: [], path: filePath };
  } catch (error) {
    return {
      success: false,
      errors: [`Failed to save data: ${(error as Error).message}`],
    };
  } finally {
    release();
  }
}

/**
 * Loads data from a JSON file in the persistence directory.
 */
export async function loadData<T extends Record<string, unknown>>(
  collection: string,
  key: string,
  config: Partial<PersistenceConfig> = {},
): Promise<LoadResult<T>> {
  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };

  const release = await persistenceLock.acquire();
  try {
    const filePath = path.join(
      effectiveConfig.base_dir,
      sanitizeFileName(collection),
      `${sanitizeFileName(key)}.json`,
    );

    if (!fs.existsSync(filePath)) {
      return {
        success: false,
        errors: [`Data not found: ${filePath}`],
      };
    }

    const content = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(content) as T;

    return { success: true, errors: [], data };
  } catch (error) {
    return {
      success: false,
      errors: [`Failed to load data: ${(error as Error).message}`],
    };
  } finally {
    release();
  }
}

/**
 * Deletes data from the persistence directory.
 */
export async function deleteData(
  collection: string,
  key: string,
  config: Partial<PersistenceConfig> = {},
): Promise<PersistenceResult> {
  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };

  const release = await persistenceLock.acquire();
  try {
    const filePath = path.join(
      effectiveConfig.base_dir,
      sanitizeFileName(collection),
      `${sanitizeFileName(key)}.json`,
    );

    if (!fs.existsSync(filePath)) {
      return {
        success: false,
        errors: [`Data not found: ${filePath}`],
      };
    }

    fs.unlinkSync(filePath);

    return { success: true, errors: [] };
  } catch (error) {
    return {
      success: false,
      errors: [`Failed to delete data: ${(error as Error).message}`],
    };
  } finally {
    release();
  }
}

/**
 * Lists all keys in a collection.
 */
export function listKeys(
  collection: string,
  config: Partial<PersistenceConfig> = {},
): string[] {
  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };
  const collectionDir = path.join(effectiveConfig.base_dir, sanitizeFileName(collection));

  if (!fs.existsSync(collectionDir)) {
    return [];
  }

  return fs
    .readdirSync(collectionDir)
    .filter((file) => file.endsWith('.json'))
    .map((file) => file.replace('.json', ''));
}

/**
 * Initializes the persistence directory structure.
 */
export function initializePersistence(
  config: Partial<PersistenceConfig> = {},
): PersistenceResult {
  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };

  try {
    ensureDir(effectiveConfig.base_dir);

    // Create subdirectories for each collection
    const collections = ['specs', 'links', 'checkpoints', 'manifests', 'heartbeats', 'traces'];
    for (const collection of collections) {
      ensureDir(path.join(effectiveConfig.base_dir, collection));
    }

    return { success: true, errors: [], path: effectiveConfig.base_dir };
  } catch (error) {
    return {
      success: false,
      errors: [`Failed to initialize persistence: ${(error as Error).message}`],
    };
  }
}

/**
 * Clears all data in the persistence directory. Intended for testing only.
 * PRODUCTION GUARD: Blocked when NODE_ENV is 'production' or when ALLOW_CLEAR is not set.
 */
export function _clearPersistence(config: Partial<PersistenceConfig> = {}): PersistenceResult {
  if (!isClearAllowed()) {
    return {
      success: false,
      errors: [clearBlockedMessage('_clearPersistence')],
    };
  }

  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };

  try {
    if (fs.existsSync(effectiveConfig.base_dir)) {
      fs.rmSync(effectiveConfig.base_dir, { recursive: true, force: true });
    }
    return { success: true, errors: [] };
  } catch (error) {
    return {
      success: false,
      errors: [`Failed to clear persistence: ${(error as Error).message}`],
    };
  }
}
