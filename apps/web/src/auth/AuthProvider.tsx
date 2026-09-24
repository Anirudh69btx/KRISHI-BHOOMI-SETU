/**
 * FLIP v3.0 — AuthContext and AuthProvider Component (Segment 01 Enhanced)
 * Manages Keycloak OIDC user state, token lifecycle, offline-first IndexedDB restoration,
 * and backend profile synchronization with NATS event sourcing.
 */

import React, { createContext, useEffect, useState, useCallback, useRef } from 'react';
import type { User } from 'oidc-client-ts';
import {
  userManager,
  loginRedirect,
  loginFarmerWithOtp,
  logoutRedirect,
} from './oidc';
import { idbTokenStore } from './idbStorage';
import { apiClient } from '../lib/apiClient';
import { useStore } from '../store';

export interface BoundFarm {
  farm_id: string;
  name: string;
  role: 'OWNER' | 'MANAGER' | 'WORKER';
  area_hectares?: number | null;
  assigned_at: string;
}

export interface ProfileSyncResponse {
  profile_id: string;
  keycloak_sub: string;
  role: string;
  full_name?: string | null;
  phone?: string | null;
  email?: string | null;
  language: string;
  preferred_channels: string[];
  mfa_enabled: boolean;
  webauthn_credential_id?: string | null;
  last_trusted_login_at?: string | null;
  last_synced_at: string;
  farms: BoundFarm[];
  permissions: string[];
}

export interface AuthContextType {
  user: User | null;
  profile: ProfileSyncResponse | null;
  roles: string[];
  tokens: {
    accessToken: string | null;
    idToken?: string;
    refreshToken?: string;
  } | null;
  isAuthenticated: boolean;
  isOfflineAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (returnUrl?: string) => Promise<void>;
  loginWithOtp: (phone: string, returnUrl?: string) => Promise<void>;
  logout: () => Promise<void>;
  syncProfile: () => Promise<ProfileSyncResponse | null>;
  revokeTrustedDevices: () => Promise<void>;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<ProfileSyncResponse | null>(null);
  const [isOfflineAuthenticated, setIsOfflineAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const setStoreAuth = useStore((s) => s.setAuth);
  const clearStoreAuth = useStore((s) => s.clearAuth);
  const isSyncing = useRef(false);

  // Sync profile with Core API
  const syncProfile = useCallback(async (): Promise<ProfileSyncResponse | null> => {
    if (isSyncing.current) return profile;
    isSyncing.current = true;

    try {
      const synced = await apiClient.post<ProfileSyncResponse>('/api/v1/auth/sync-profile');
      setProfile(synced);

      // Sync Zustand global store
      if (user) {
        setStoreAuth(
          {
            id: synced.profile_id,
            role: (synced.role || 'farmer') as any,
            full_name: synced.full_name || user.profile.name || 'User',
            phone_number: synced.phone || undefined,
            preferred_language: (synced.language === 'hi' ? 'hi' : 'en'),
            metadata: {
              email: synced.email || user.profile.email || '',
              roles: synced.permissions.length ? synced.permissions : [synced.role],
              last_synced_at: synced.last_synced_at,
            },
          },
          user.access_token,
        );
      }
      return synced;
    } catch (err: any) {
      console.warn('[AuthProvider] Profile sync warning (offline or transient):', err?.message || err);
      return null;
    } finally {
      isSyncing.current = false;
    }
  }, [user, profile, setStoreAuth]);

  // Handle user session changes
  const handleUserLoaded = useCallback(
    async (loadedUser: User | null) => {
      if (!loadedUser || loadedUser.expired) {
        setUser(null);
        setProfile(null);
        setIsOfflineAuthenticated(false);
        clearStoreAuth();
        setIsLoading(false);
        return;
      }

      setUser(loadedUser);
      setIsOfflineAuthenticated(!navigator.onLine);
      setIsLoading(false);

      // Perform profile sync in background if online
      if (navigator.onLine) {
        try {
          await syncProfile();
        } catch (e) {
          console.error('[AuthProvider] Background sync error:', e);
        }
      }
    },
    [clearStoreAuth, syncProfile],
  );

  // Setup OIDC event listeners & offline restoration
  useEffect(() => {
    let isMounted = true;

    // Load initial user session (from IndexedDB encrypted store via UserManager)
    userManager
      .getUser()
      .then(async (existingUser) => {
        if (!isMounted) return;

        if (existingUser && !existingUser.expired) {
          handleUserLoaded(existingUser);
        } else if (!navigator.onLine) {
          // Offline fallback: check if we have cached user keys in IDB
          const keys = await idbTokenStore.getAllKeys();
          if (keys.length > 0) {
            console.log('[AuthProvider] Offline cold start: Restoring cached IDB identity session.');
            setIsOfflineAuthenticated(true);
          }
          setIsLoading(false);
        } else {
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('[AuthProvider] Initial user fetch failed:', err);
          setIsLoading(false);
        }
      });

    const onUserLoaded = (u: User) => handleUserLoaded(u);
    const onUserUnloaded = () => {
      setUser(null);
      setProfile(null);
      setIsOfflineAuthenticated(false);
      clearStoreAuth();
    };
    const onSilentRenewError = (err: Error) => {
      console.error('[AuthProvider] Silent renew error:', err);
      // Do not clear session if offline
      if (navigator.onLine) {
        setError('Session renewal failed');
      }
    };

    userManager.events.addUserLoaded(onUserLoaded);
    userManager.events.addUserUnloaded(onUserUnloaded);
    userManager.events.addSilentRenewError(onSilentRenewError);

    // Online/offline listeners
    const handleOnline = () => {
      setIsOfflineAuthenticated(false);
      syncProfile();
    };
    const handleOffline = () => {
      setIsOfflineAuthenticated(true);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      isMounted = false;
      userManager.events.removeUserLoaded(onUserLoaded);
      userManager.events.removeUserUnloaded(onUserUnloaded);
      userManager.events.removeSilentRenewError(onSilentRenewError);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [handleUserLoaded, clearStoreAuth, syncProfile]);

  const login = useCallback(async (returnUrl?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await loginRedirect(returnUrl);
    } catch (err: any) {
      setError(err?.message || 'Login redirect failed');
      setIsLoading(false);
    }
  }, []);

  const loginWithOtp = useCallback(async (phone: string, returnUrl?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await loginFarmerWithOtp(phone, returnUrl);
    } catch (err: any) {
      setError(err?.message || 'Farmer OTP login failed');
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await logoutRedirect();
    } finally {
      setUser(null);
      setProfile(null);
      setIsOfflineAuthenticated(false);
      clearStoreAuth();
      setIsLoading(false);
    }
  }, [clearStoreAuth]);

  const revokeTrustedDevices = useCallback(async () => {
    try {
      await apiClient.delete('/api/v1/auth/trusted-devices');
      await logout();
    } catch (err: any) {
      console.error('[AuthProvider] Failed to revoke trusted devices:', err);
    }
  }, [logout]);

  const userRoles: string[] = user
    ? profile?.permissions ||
      (user.profile['realm_access'] as { roles?: string[] })?.roles ||
      []
    : [];

  const hasRole = useCallback(
    (role: string): boolean => {
      if (!user) return false;
      return userRoles.includes(role) || userRoles.includes('platform_admin');
    },
    [user, userRoles],
  );

  const hasAnyRole = useCallback(
    (roles: string[]): boolean => {
      if (!user) return false;
      return roles.some((r) => hasRole(r));
    },
    [user, hasRole],
  );

  const value: AuthContextType = {
    user,
    profile,
    roles: userRoles,
    tokens: user
      ? {
          accessToken: user.access_token,
          idToken: user.id_token,
          refreshToken: user.refresh_token,
        }
      : null,
    isAuthenticated: (!!user && !user.expired) || isOfflineAuthenticated,
    isOfflineAuthenticated,
    isLoading,
    error,
    login,
    loginWithOtp,
    logout,
    syncProfile,
    revokeTrustedDevices,
    hasRole,
    hasAnyRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
