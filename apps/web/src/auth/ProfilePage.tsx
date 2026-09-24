/**
 * FLIP v3.0 — User Profile & Farm Binding Management (Segment 01 Enhanced)
 * Displays Keycloak synced identity, role badge, MFA status, WebAuthn passkey registration,
 * trusted device session revocation, and bound farms with Row-Level Security.
 */

import React, { useState } from 'react';
import { useAuth } from './useAuth';
import { useFarmBinding } from '../hooks/useFarmBinding';
import { apiClient } from '../lib/apiClient';
import './authStyles.css';

export const ProfilePage: React.FC = () => {
  const { user, profile, logout, syncProfile, revokeTrustedDevices, isLoading: authLoading } = useAuth();
  const { farms, isLoading: farmsLoading, bindFarm } = useFarmBinding();

  const [newFarmId, setNewFarmId] = useState<string>('');
  const [bindRole, setBindRole] = useState<'OWNER' | 'MANAGER' | 'WORKER'>('OWNER');
  const [bindError, setBindError] = useState<string | null>(null);
  const [bindSuccess, setBindSuccess] = useState<string | null>(null);
  const [isBinding, setIsBinding] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [isRegisteringPasskey, setIsRegisteringPasskey] = useState<boolean>(false);

  const handleManualSync = async () => {
    setIsSyncing(true);
    try {
      await syncProfile();
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRegisterPasskey = async () => {
    if (!window.PublicKeyCredential) {
      alert('WebAuthn Passkeys are not supported on this browser.');
      return;
    }

    setIsRegisteringPasskey(true);
    try {
      const options = await apiClient.get<any>('/api/v1/auth/webauthn/register-options');
      const challengeBytes = Uint8Array.from(atob(options.challenge), (c) => c.charCodeAt(0));
      const userIdBytes = Uint8Array.from(atob(options.user.id), (c) => c.charCodeAt(0));

      const credential = (await navigator.credentials.create({
        publicKey: {
          challenge: challengeBytes,
          rp: options.rp,
          user: {
            id: userIdBytes,
            name: options.user.name,
            displayName: options.user.displayName,
          },
          pubKeyCredParams: options.pubKeyCredParams,
          authenticatorSelection: options.authenticatorSelection,
          timeout: options.timeout,
          attestation: options.attestation,
        },
      })) as any;

      if (credential) {
        await apiClient.post('/api/v1/auth/webauthn/register-verify', {
          id: credential.id,
          rawId: credential.id,
        });
        await syncProfile();
        alert('WebAuthn Passkey enrolled successfully!');
      }
    } catch (err: any) {
      console.warn('[WebAuthn] Registration error:', err);
      alert('Passkey registration: ' + (err?.message || 'Cancelled by user'));
    } finally {
      setIsRegisteringPasskey(false);
    }
  };

  const handleRevokeDevices = async () => {
    if (window.confirm('Are you sure you want to revoke all 30-day trusted devices and log out from all sessions?')) {
      await revokeTrustedDevices();
    }
  };

  const handleAddFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    setBindError(null);
    setBindSuccess(null);

    if (!newFarmId.trim()) {
      setBindError('Please enter a valid Farm UUID');
      return;
    }

    setIsBinding(true);
    try {
      const success = await bindFarm({ farm_id: newFarmId.trim(), role: bindRole });
      if (success) {
        setBindSuccess('Farm bound successfully!');
        setNewFarmId('');
      } else {
        setBindError('Failed to bind farm. Please ensure the Farm ID is valid.');
      }
    } finally {
      setIsBinding(false);
    }
  };

  const role = profile?.role || 'farmer';
  const fullName = profile?.full_name || user?.profile.name || 'FLIP Farmer';
  const phone = profile?.phone || user?.profile['phone_number'] || 'Not linked';
  const email = profile?.email || user?.profile.email || 'Not linked';

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '2rem 1.5rem' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 800, color: '#064e3b', margin: '0 0 0.25rem' }}>
            🌾 User Profile &amp; Security Settings
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
            Identity synchronized with Keycloak IdP • Event-Sourced via NATS JetStream
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="flip-btn-secondary"
            onClick={handleManualSync}
            disabled={isSyncing || authLoading}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', width: 'auto' }}
          >
            {isSyncing ? 'Syncing...' : '🔄 Sync from Keycloak'}
          </button>
          <button
            type="button"
            onClick={handleRevokeDevices}
            style={{
              padding: '0.5rem 1rem',
              background: '#fff1f2',
              color: '#e11d48',
              border: '1px solid #fecdd3',
              borderRadius: '0.75rem',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            Revoke All Devices
          </button>
          <button
            type="button"
            onClick={logout}
            style={{
              padding: '0.5rem 1rem',
              background: '#fee2e2',
              color: '#991b1b',
              border: '1px solid #fca5a5',
              borderRadius: '0.75rem',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            Log Out
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {/* User Details Card */}
        <div
          style={{
            background: '#ffffff',
            borderRadius: '1rem',
            padding: '1.75rem',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
            border: '1px solid #e5e7eb',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
            <div
              style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                fontWeight: 700,
              }}
            >
              {fullName.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827', margin: '0 0 0.25rem' }}>
                {fullName}
              </h2>
              <span className={`flip-role-badge ${role}`}>
                {role === 'farmer' ? '🌾 Farmer' : role === 'agronomist' ? '🔬 Agronomist' : `🛡️ ${role}`}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.875rem' }}>
            <div>
              <span style={{ color: '#6b7280', display: 'block', marginBottom: '0.15rem' }}>Mobile Number:</span>
              <strong style={{ color: '#111827' }}>{phone}</strong>
            </div>

            <div>
              <span style={{ color: '#6b7280', display: 'block', marginBottom: '0.15rem' }}>Email Address:</span>
              <strong style={{ color: '#111827' }}>{email}</strong>
            </div>

            <div>
              <span style={{ color: '#6b7280', display: 'block', marginBottom: '0.15rem' }}>Keycloak Subject UUID:</span>
              <code style={{ fontSize: '0.75rem', background: '#f3f4f6', padding: '0.2rem 0.4rem', borderRadius: '4px' }}>
                {profile?.keycloak_sub || user?.profile.sub || 'Pending'}
              </code>
            </div>

            <div>
              <span style={{ color: '#6b7280', display: 'block', marginBottom: '0.15rem' }}>Security &amp; Passkeys:</span>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                <span style={{ color: profile?.webauthn_credential_id ? '#059669' : '#d97706', fontWeight: 600 }}>
                  {profile?.webauthn_credential_id ? '✅ Passkey Registered' : '⚠️ SMS OTP Active'}
                </span>
                <button
                  type="button"
                  onClick={handleRegisterPasskey}
                  disabled={isRegisteringPasskey}
                  style={{
                    background: '#f0fdf4',
                    border: '1px solid #86efac',
                    color: '#15803d',
                    padding: '0.3rem 0.6rem',
                    borderRadius: '0.5rem',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {isRegisteringPasskey ? 'Enrolling...' : '+ Add Passkey'}
                </button>
              </div>
            </div>

            <div>
              <span style={{ color: '#6b7280', display: 'block', marginBottom: '0.15rem' }}>Preferred Language:</span>
              <span style={{ textTransform: 'uppercase', fontWeight: 600, color: '#065f46' }}>
                {profile?.language || 'hi'} (Hindi)
              </span>
            </div>

            <div>
              <span style={{ color: '#6b7280', display: 'block', marginBottom: '0.15rem' }}>Last Synced with IdP:</span>
              <span style={{ color: '#4b5563' }}>
                {profile?.last_synced_at ? new Date(profile.last_synced_at).toLocaleString() : 'Just now'}
              </span>
            </div>
          </div>
        </div>

        {/* Farm Binding Card */}
        <div
          style={{
            background: '#ffffff',
            borderRadius: '1rem',
            padding: '1.75rem',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
            border: '1px solid #e5e7eb',
          }}
        >
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827', margin: '0 0 0.5rem' }}>
            🏡 Bound Farms
          </h2>
          <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: '0 0 1.25rem' }}>
            Farms currently linked to your profile via <code>farmer_farms</code> table (RLS enabled).
          </p>

          {farmsLoading ? (
            <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Loading bound farms...</p>
          ) : farms.length === 0 ? (
            <div
              style={{
                padding: '1.5rem',
                background: '#f9fafb',
                borderRadius: '0.75rem',
                textAlign: 'center',
                color: '#6b7280',
                fontSize: '0.875rem',
                marginBottom: '1.5rem',
              }}
            >
              No farms bound yet. Bind a farm below to view sensors and digital twin.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
              {farms.map((f) => (
                <div
                  key={f.farm_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.875rem 1rem',
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: '0.75rem',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#065f46' }}>{f.name}</div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                      {f.area_hectares ? `${f.area_hectares} ha` : 'Area pending'} • Role: {f.role}
                    </div>
                  </div>
                  <span style={{ fontSize: '0.75rem', background: '#dcfce7', color: '#166534', padding: '0.2rem 0.5rem', borderRadius: '999px', fontWeight: 600 }}>
                    Active
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Add Farm Form */}
          <form onSubmit={handleAddFarm} style={{ borderTop: '1px solid #f3f4f6', paddingTop: '1.25rem' }}>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#374151', margin: '0 0 0.75rem' }}>
              + Bind New Farm
            </h3>

            {bindError && (
              <div style={{ color: '#991b1b', fontSize: '0.8125rem', marginBottom: '0.5rem' }}>
                {bindError}
              </div>
            )}
            {bindSuccess && (
              <div style={{ color: '#065f46', fontSize: '0.8125rem', marginBottom: '0.5rem' }}>
                {bindSuccess}
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <input
                type="text"
                value={newFarmId}
                onChange={(e) => setNewFarmId(e.target.value)}
                placeholder="Farm UUID (e.g. 33333333-3333...)"
                style={{
                  flex: 2,
                  padding: '0.625rem 0.875rem',
                  border: '1.5px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  outline: 'none',
                }}
              />
              <select
                value={bindRole}
                onChange={(e) => setBindRole(e.target.value as any)}
                style={{
                  flex: 1,
                  padding: '0.625rem 0.5rem',
                  border: '1.5px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  background: '#ffffff',
                }}
              >
                <option value="OWNER">Owner</option>
                <option value="MANAGER">Manager</option>
                <option value="WORKER">Worker</option>
              </select>
            </div>

            <button
              type="submit"
              className="flip-btn-primary"
              disabled={isBinding || !newFarmId.trim()}
              style={{ padding: '0.625rem 1rem', fontSize: '0.875rem' }}
            >
              {isBinding ? 'Binding Farm...' : 'Bind Farm →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
