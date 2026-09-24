/**
 * FLIP v3.0 — useProfileSync Hook (Segment 01)
 * Automates synchronization of Keycloak identity claims with PostgreSQL profiles table.
 */

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../auth/useAuth';
import type { ProfileSyncResponse } from '../auth/AuthProvider';

export function useProfileSync() {
  const { profile, syncProfile, tokens, isAuthenticated } = useAuth();
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const triggerSync = useCallback(async (): Promise<ProfileSyncResponse | null> => {
    if (!isAuthenticated) return null;
    setIsSyncing(true);
    setSyncError(null);
    try {
      const result = await syncProfile();
      return result;
    } catch (err: any) {
      setSyncError(err?.message || 'Profile sync failed');
      return null;
    } finally {
      setIsSyncing(false);
    }
  }, [isAuthenticated, syncProfile]);

  // Trigger sync on token changes or login
  useEffect(() => {
    if (isAuthenticated && tokens?.accessToken && !profile) {
      triggerSync();
    }
  }, [isAuthenticated, tokens?.accessToken, profile, triggerSync]);

  return {
    profile,
    isSyncing,
    syncError,
    triggerSync,
  };
}

export default useProfileSync;
