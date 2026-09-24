/**
 * FLIP v3.0 — OIDC PKCE Callback Handler (Segment 01)
 * Processes authorization_code, exchanges tokens, syncs profile, and redirects.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { handleOidcCallback } from '../auth/oidc';
import { useAuth } from '../auth/useAuth';

export const AuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const { syncProfile } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function processCallback() {
      try {
        const user = await handleOidcCallback();
        // Sync profile to database
        await syncProfile();

        if (active) {
          const returnUrl = (user.state as { returnUrl?: string })?.returnUrl || '/dashboard';
          navigate(returnUrl, { replace: true });
        }
      } catch (err: any) {
        console.error('[AuthCallback] Error processing OIDC token exchange:', err);
        if (active) {
          setError(err?.message || 'Authentication callback failed. Returning to login...');
          setTimeout(() => {
            navigate('/login', { replace: true });
          }, 3000);
        }
      }
    }

    processCallback();

    return () => {
      active = false;
    };
  }, [navigate, syncProfile]);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'radial-gradient(circle at 10% 20%, rgba(6, 78, 59, 0.95) 0%, rgba(2, 44, 34, 1) 90%)',
        color: '#ffffff',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          background: 'rgba(255, 255, 255, 0.98)',
          borderRadius: '1.25rem',
          padding: '2.5rem',
          maxWidth: '420px',
          width: '100%',
          textAlign: 'center',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.45)',
          color: '#1f2937',
        }}
      >
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🌾</div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#065f46', margin: '0 0 0.5rem' }}>
          {error ? 'Authentication Error' : 'Securing Session...'}
        </h2>
        <p style={{ fontSize: '0.9375rem', color: '#4b5563', margin: 0 }}>
          {error || 'Exchanging authorization tokens and synchronizing farmer profile with FLIP platform.'}
        </p>
        {!error && (
          <div style={{ marginTop: '1.5rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                border: '3px solid #e5e7eb',
                borderTop: '3px solid #059669',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto',
              }}
            />
            <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthCallbackPage;
