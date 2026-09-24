/**
 * FLIP v3.0 — useFarmBinding Hook (Segment 01)
 * Manages fetching bound farms and binding new farms to the current farmer.
 */

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../lib/apiClient';
import { useAuth } from '../auth/useAuth';
import type { BoundFarm } from '../auth/AuthProvider';

export interface FarmBindingPayload {
  farm_id: string;
  role: 'OWNER' | 'MANAGER' | 'WORKER';
}

export function useFarmBinding() {
  const { isAuthenticated, syncProfile } = useAuth();
  const [farms, setFarms] = useState<BoundFarm[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFarms = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<BoundFarm[]>('/api/v1/farmers/me/farms');
      setFarms(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load bound farms');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const bindFarm = useCallback(
    async (payload: FarmBindingPayload): Promise<boolean> => {
      setIsLoading(true);
      setError(null);
      try {
        await apiClient.put('/api/v1/farmers/me/farms', payload);
        await fetchFarms();
        await syncProfile();
        return true;
      } catch (err: any) {
        setError(err?.message || 'Failed to bind farm');
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [fetchFarms, syncProfile],
  );

  useEffect(() => {
    fetchFarms();
  }, [fetchFarms]);

  return {
    farms,
    isLoading,
    error,
    refetchFarms: fetchFarms,
    bindFarm,
  };
}

export default useFarmBinding;
