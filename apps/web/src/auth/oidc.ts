/**
 * FLIP v3.0 — OIDC Client Configuration (Segment 01)
 * Enforces Keycloak OIDC PKCE flow, silent renew, and OTP challenge parameters.
 */

import { UserManager, type User, Log } from 'oidc-client-ts';

// Debug logging in development
if (import.meta.env.DEV) {
  Log.setLevel(Log.INFO);
  Log.setLogger(console);
}

import { idbTokenStore } from './idbStorage';

const KEYCLOAK_BASE = import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080';
const REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'flip';
const CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'flip-web';

export const oidcConfig = {
  authority: `${KEYCLOAK_BASE}/realms/${REALM}`,
  client_id: CLIENT_ID,
  redirect_uri: `${window.location.origin}/auth/callback`,
  post_logout_redirect_uri: `${window.location.origin}/login`,
  response_type: 'code',
  scope: 'openid profile email offline_access roles',
  automaticSilentRenew: true,
  silent_redirect_uri: `${window.location.origin}/auth/silent-renew.html`,
  userStore: idbTokenStore as any,
  clockSkewInSeconds: 300,
  filterProtocolClaims: true,
  loadUserInfo: true,
};

export const userManager = new UserManager(oidcConfig);

/**
 * Standard OIDC PKCE Login redirect to Keycloak.
 */
export async function loginRedirect(returnUrl?: string): Promise<void> {
  await userManager.signinRedirect({
    state: { returnUrl: returnUrl || window.location.pathname },
  });
}

/**
 * Farmer Login redirect to Keycloak custom 'otp-login' flow or required action.
 */
export async function loginFarmerWithOtp(phoneNumber?: string, returnUrl?: string): Promise<void> {
  const extraQueryParams: Record<string, string> = {};
  if (phoneNumber) {
    extraQueryParams.phone = phoneNumber;
  }
  // Point directly to the custom OTP authentication flow if configured
  extraQueryParams.kc_action = 'flip-twilio-sms-action';

  await userManager.signinRedirect({
    state: { returnUrl: returnUrl || '/dashboard', mode: 'otp' },
    extraQueryParams,
  });
}

/**
 * Trigger logout and clear tokens.
 */
export async function logoutRedirect(): Promise<void> {
  try {
    await userManager.signoutRedirect();
  } catch {
    await userManager.removeUser();
    window.location.href = '/login';
  }
}

/**
 * Handle OIDC callback at /auth/callback.
 */
export async function handleOidcCallback(): Promise<User> {
  return await userManager.signinRedirectCallback();
}

/**
 * Retrieve cached or refreshed access token.
 */
export async function getValidAccessToken(): Promise<string | null> {
  const user = await userManager.getUser();
  if (!user || user.expired) {
    try {
      const renewedUser = await userManager.signinSilent();
      return renewedUser?.access_token ?? null;
    } catch {
      return null;
    }
  }
  return user.access_token;
}
