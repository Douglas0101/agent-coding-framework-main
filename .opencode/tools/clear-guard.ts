/**
 * clear-guard.ts
 *
 * Shared production guard for destructive test-only clear operations.
 * Blocking rule:
 *   - In production, clearing is blocked unless ALLOW_CLEAR is explicitly "1"
 *   - In test/dev environments, clear helpers remain available
 */

export function isClearAllowed(): boolean {
  if (process.env.ALLOW_CLEAR === '1') {
    return true;
  }
  return process.env.NODE_ENV !== 'production';
}

export function clearBlockedMessage(operation: string): string {
  return `${operation} is blocked in production. Set ALLOW_CLEAR=1 to override (testing only).`;
}
