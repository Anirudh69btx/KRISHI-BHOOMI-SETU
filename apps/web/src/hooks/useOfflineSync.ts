/**
 * FLIP v3.0 — Offline Sync Hook
 * Uses Background Sync API + IndexedDB queue fallback.
 * Drains pendingActions from Zustand store when connectivity is restored.
 */

import { useEffect, useCallback } from 'react';
import { useStore } from '../store';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface SyncableAction {
  id: string;
  type: string;
  payload: unknown;
  retries: number;
}

async function executeAction(action: SyncableAction, token: string | null): Promise<boolean> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    switch (action.type) {
      case 'SENSOR_MANUAL_ENTRY': {
        const res = await fetch(`${API_BASE}/api/v1/sensors/manual`, {
          method: 'POST',
          headers,
          body: JSON.stringify(action.payload),
        });
        return res.ok;
      }
      case 'ADVISORY_ACK': {
        const { advisoryId } = action.payload as { advisoryId: string };
        const res = await fetch(`${API_BASE}/api/v1/advisories/${advisoryId}/acknowledge`, {
          method: 'POST',
          headers,
        });
        return res.ok;
      }
      case 'FARMER_ACTION_LOG': {
        const res = await fetch(`${API_BASE}/api/v1/actions`, {
          method: 'POST',
          headers,
          body: JSON.stringify(action.payload),
        });
        return res.ok;
      }
      default:
        console.warn('[Sync] Unknown action type:', action.type);
        return true; // Drop unknown actions
    }
  } catch {
    return false;
  }
}

export function useOfflineSync() {
  const isOnline = useStore((s) => s.isOnline);
  const pendingActions = useStore((s) => s.pendingActions);
  const dequeueAction = useStore((s) => s.dequeueAction);
  const setOnline = useStore((s) => s.setOnline);
  const accessToken = useStore((s) => s.accessToken);

  // Track network status
  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [setOnline]);

  // Drain queue when online
  const drainQueue = useCallback(async () => {
    if (!isOnline || pendingActions.length === 0) return;

    console.info(`[Sync] Draining ${pendingActions.length} pending actions...`);

    for (const action of [...pendingActions]) {
      const success = await executeAction(action, accessToken);
      if (success) {
        dequeueAction(action.id);
        console.debug(`[Sync] Action ${action.id} (${action.type}) synced successfully`);
      } else if (action.retries >= 3) {
        // Drop after 3 retries to avoid infinite loops
        console.error(`[Sync] Action ${action.id} dropped after ${action.retries} retries`);
        dequeueAction(action.id);
      }
    }
  }, [isOnline, pendingActions, dequeueAction, accessToken]);

  useEffect(() => {
    if (isOnline) {
      drainQueue();
    }
  }, [isOnline, drainQueue]);

  return {
    isOnline,
    pendingCount: pendingActions.length,
    drainQueue,
  };
}
