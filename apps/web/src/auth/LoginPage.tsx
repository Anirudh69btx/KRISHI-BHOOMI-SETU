/**
 * FLIP v3.0 — Unified Login Page (Segment 01)
 * Offers Farmer Login (Phone -> SMS OTP) & Expert/Admin SSO (Keycloak Hosted MFA).
 */

import React, { useState } from 'react';
import { useAuth } from './useAuth';
import { OTPScreen } from './OTPScreen';
import { ExpertLoginTab } from './ExpertLoginTab';
import { apiClient } from '../lib/apiClient';
import './authStyles.css';

export const LoginPage: React.FC = () => {
  const { loginWithOtp, isLoading: authLoading, error: authError } = useAuth();

  const [activeTab, setActiveTab] = useState<'farmer' | 'expert'>('farmer');
  const [phoneNumber, setPhoneNumber] = useState<string>('');
  const [showOtpScreen, setShowOtpScreen] = useState<boolean>(false);
  const [otpLoading, setOtpLoading] = useState<boolean>(false);
  const [otpError, setOtpError] = useState<string | null>(null);

  // Normalize phone number to +91 if needed
  const formatPhone = (raw: string): string => {
    let clean = raw.replace(/\D/g, '');
    if (clean.length === 10) {
      return `+91${clean}`;
    }
    if (!raw.startsWith('+')) {
      return `+${clean}`;
    }
    return raw;
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setOtpError(null);

    const formatted = formatPhone(phoneNumber);
    if (formatted.length < 12) {
      setOtpError('Please enter a valid 10-digit mobile number');
      return;
    }

    setOtpLoading(true);
    try {
      // 1. Dispatch SMS OTP (Twilio Verify or Dev Mock)
      await apiClient.post('/api/v1/auth/otp/send', { phone: formatted }, { skipAuth: true });
      setShowOtpScreen(true);
    } catch (err: any) {
      console.warn('API OTP send failed, falling back to Keycloak flow:', err);
      // Fallback directly to Keycloak OTP redirection
      await loginWithOtp(formatted, '/dashboard');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleVerifyOtp = async (code: string) => {
    setOtpLoading(true);
    setOtpError(null);
    const formatted = formatPhone(phoneNumber);

    try {
      // Verify with backend
      const res = await apiClient.post<{ verified: boolean }>(
        '/api/v1/auth/otp/verify',
        { phone: formatted, otp: code },
        { skipAuth: true },
      );

      if (res.verified) {
        // Hand off to Keycloak session establishment with OTP challenge approved
        await loginWithOtp(formatted, '/dashboard');
      }
    } catch (err: any) {
      setOtpError(err?.message || 'Invalid OTP code. Please enter 123456 in dev mode.');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResendOtp = async () => {
    const formatted = formatPhone(phoneNumber);
    await apiClient.post('/api/v1/auth/otp/send', { phone: formatted }, { skipAuth: true });
  };

  return (
    <div className="flip-auth-container">
      <div className="flip-auth-card">
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.25rem' }}>🌾</div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#064e3b', margin: 0, letterSpacing: '-0.02em' }}>
            KRISHI BHOOMI SETU
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#059669', fontWeight: 600, marginTop: '0.25rem' }}>
            Farm Lifecycle Intelligence Platform (FLIP v3.0)
          </p>
        </div>

        {/* Tab Selection */}
        {!showOtpScreen && (
          <div className="flip-auth-tabs">
            <button
              type="button"
              className={`flip-auth-tab ${activeTab === 'farmer' ? 'active' : ''}`}
              onClick={() => setActiveTab('farmer')}
            >
              🌾 Farmer Login
            </button>
            <button
              type="button"
              className={`flip-auth-tab ${activeTab === 'expert' ? 'active' : ''}`}
              onClick={() => setActiveTab('expert')}
            >
              🏢 Expert / Admin
            </button>
          </div>
        )}

        {/* Global Error Banner */}
        {authError && (
          <div
            style={{
              background: '#fee2e2',
              border: '1px solid #f87171',
              borderRadius: '0.5rem',
              padding: '0.75rem 1rem',
              color: '#991b1b',
              fontSize: '0.875rem',
              marginBottom: '1rem',
            }}
          >
            {authError}
          </div>
        )}

        {/* View 1: Farmer OTP Screen */}
        {showOtpScreen ? (
          <OTPScreen
            phone={formatPhone(phoneNumber)}
            onVerify={handleVerifyOtp}
            onResend={handleResendOtp}
            onChangePhone={() => setShowOtpScreen(false)}
            isLoading={otpLoading || authLoading}
            error={otpError}
          />
        ) : activeTab === 'farmer' ? (
          /* View 2: Farmer Mobile Input */
          <div>
            <p style={{ fontSize: '0.9375rem', color: '#4b5563', marginBottom: '1.25rem', lineHeight: 1.5 }}>
              Enter your mobile number. We will send a 6-digit OTP code to verify your identity.
            </p>

            {otpError && (
              <div
                style={{
                  background: '#fee2e2',
                  border: '1px solid #f87171',
                  borderRadius: '0.5rem',
                  padding: '0.75rem 1rem',
                  color: '#991b1b',
                  fontSize: '0.875rem',
                  marginBottom: '1rem',
                }}
              >
                {otpError}
              </div>
            )}

            <form onSubmit={handleSendOtp}>
              <div style={{ marginBottom: '1.25rem' }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    color: '#374151',
                    marginBottom: '0.5rem',
                  }}
                >
                  Mobile Number (मोबाइल नंबर)
                </label>
                <div style={{ position: 'relative' }}>
                  <span
                    style={{
                      position: 'absolute',
                      left: '1rem',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: '#6b7280',
                    }}
                  >
                    🇮🇳 +91
                  </span>
                  <input
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="98765 43210"
                    maxLength={13}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      padding: '0.875rem 1rem 0.875rem 4.5rem',
                      border: '1.5px solid #d1d5db',
                      borderRadius: '0.75rem',
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: '#111827',
                      outline: 'none',
                    }}
                    required
                    autoFocus
                  />
                </div>
              </div>

              <button
                type="submit"
                className="flip-btn-primary"
                disabled={otpLoading || !phoneNumber.trim()}
              >
                {otpLoading ? 'Sending OTP Code...' : 'Get Login OTP →'}
              </button>
            </form>

            <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
              <button
                type="button"
                onClick={() => loginWithOtp(phoneNumber ? formatPhone(phoneNumber) : '', '/dashboard')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#059669',
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                Or proceed directly via Keycloak OTP Flow
              </button>
            </div>
          </div>
        ) : (
          /* View 3: Expert / Agronomist / FPO Admin Passkey (WebAuthn) Login */
          <ExpertLoginTab />
        )}

        {/* Footer */}
        <div
          style={{
            marginTop: '2rem',
            paddingTop: '1.25rem',
            borderTop: '1px solid #f3f4f6',
            textAlign: 'center',
            fontSize: '0.75rem',
            color: '#9ca3af',
          }}
        >
          Protected by Keycloak IAM &amp; Twilio Verify • AES-256 Encrypted
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
