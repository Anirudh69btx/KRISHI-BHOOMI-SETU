/**
 * FLIP v3.0 — 6-Digit OTP Verification Screen (Segment 01)
 * Features: Auto-advance, backspace navigation, paste support, 60s resend timer.
 */

import React, { useState, useEffect, useRef } from 'react';
import './authStyles.css';

interface OTPScreenProps {
  phone: string;
  onVerify: (otp: string) => Promise<void>;
  onResend: () => Promise<void>;
  onChangePhone: () => void;
  isLoading?: boolean;
  error?: string | null;
}

export const OTPScreen: React.FC<OTPScreenProps> = ({
  phone,
  onVerify,
  onResend,
  onChangePhone,
  isLoading = false,
  error = null,
}) => {
  const [digits, setDigits] = useState<string[]>(['', '', '', '', '', '']);
  const [timer, setTimer] = useState<number>(60);
  const [isResending, setIsResending] = useState<boolean>(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // 60-second countdown for resend
  useEffect(() => {
    if (timer <= 0) return;
    const interval = setInterval(() => {
      setTimer((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [timer]);

  // Focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = (index: number, value: string) => {
    const char = value.slice(-1); // Only take last character
    if (char && !/^\d$/.test(char)) return; // Only numbers allowed

    const newDigits = [...digits];
    newDigits[index] = char;
    setDigits(newDigits);

    // Auto-advance to next input
    if (char && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit if all 6 digits entered
    if (char && index === 5) {
      const fullOtp = newDigits.join('');
      if (fullOtp.length === 6) {
        onVerify(fullOtp);
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (!digits[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
        const newDigits = [...digits];
        newDigits[index - 1] = '';
        setDigits(newDigits);
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData('text').trim();
    if (!/^\d{6}$/.test(pasteData)) return;

    const newDigits = pasteData.split('');
    setDigits(newDigits);
    inputRefs.current[5]?.focus();
    onVerify(pasteData);
  };

  const handleResend = async () => {
    if (timer > 0 || isResending) return;
    setIsResending(true);
    try {
      await onResend();
      setTimer(60);
      setDigits(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsResending(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const otp = digits.join('');
    if (otp.length === 6) {
      onVerify(otp);
    }
  };

  return (
    <div className="flip-otp-screen">
      <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🌾</div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#065f46', margin: '0 0 0.5rem' }}>
          Enter Verification Code
        </h2>
        <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
          We sent a 6-digit OTP to <strong>{phone}</strong>
        </p>
        <button
          type="button"
          onClick={onChangePhone}
          style={{
            background: 'none',
            border: 'none',
            color: '#059669',
            fontSize: '0.8125rem',
            fontWeight: 600,
            cursor: 'pointer',
            marginTop: '0.35rem',
            textDecoration: 'underline',
          }}
        >
          Change Phone Number
        </button>
      </div>

      {error && (
        <div
          style={{
            background: '#fee2e2',
            border: '1px solid #f87171',
            borderRadius: '0.5rem',
            padding: '0.75rem 1rem',
            color: '#991b1b',
            fontSize: '0.875rem',
            marginBottom: '1rem',
            textAlign: 'center',
          }}
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="flip-otp-inputs">
          {digits.map((digit, index) => (
            <input
              key={index}
              ref={(el) => (inputRefs.current[index] = el)}
              className={`flip-otp-digit ${digit ? 'filled' : ''}`}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={handlePaste}
              disabled={isLoading}
              autoComplete="one-time-code"
            />
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', margin: '1rem 0' }}>
          <input
            type="checkbox"
            id="rememberDeviceCheckbox"
            defaultChecked
            style={{ width: '1.125rem', height: '1.125rem', accentColor: '#059669', cursor: 'pointer' }}
          />
          <label htmlFor="rememberDeviceCheckbox" style={{ fontSize: '0.875rem', color: '#4b5563', cursor: 'pointer' }}>
            Remember me on this device (30-day trusted session)
          </label>
        </div>

        <button
          type="submit"
          className="flip-btn-primary"
          disabled={isLoading || digits.join('').length !== 6}
          style={{ marginTop: '0.5rem' }}
        >
          {isLoading ? (
            <span>Verifying Code...</span>
          ) : (
            <span>Verify &amp; Continue →</span>
          )}
        </button>
      </form>

      <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
        {timer > 0 ? (
          <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
            Resend OTP in <strong>{timer}s</strong>
          </p>
        ) : (
          <button
            type="button"
            onClick={handleResend}
            disabled={isResending}
            style={{
              background: 'none',
              border: 'none',
              color: '#059669',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            {isResending ? 'Sending new code...' : 'Resend OTP via SMS'}
          </button>
        )}
      </div>
    </div>
  );
};

export default OTPScreen;
