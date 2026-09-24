/**
 * FLIP v3.0 — Role Guard Component & HOC (Segment 01)
 * Restricts UI rendering based on Keycloak realm roles.
 */

import React from 'react';
import { useAuth } from './useAuth';
import './authStyles.css';

interface RoleGuardProps {
  roles: string[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const RoleGuard: React.FC<RoleGuardProps> = ({ roles, children, fallback }) => {
  const { hasAnyRole, isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div style={{ padding: '1rem', color: '#6b7280', textAlign: 'center' }}>
        Verifying permissions...
      </div>
    );
  }

  if (!isAuthenticated || !hasAnyRole(roles)) {
    if (fallback !== undefined) {
      return <>{fallback}</>;
    }

    return (
      <div
        style={{
          padding: '2rem',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '0.75rem',
          textAlign: 'center',
          color: '#991b1b',
          margin: '1.5rem 0',
        }}
      >
        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔒</div>
        <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: '0 0 0.5rem' }}>
          Access Restricted
        </h3>
        <p style={{ fontSize: '0.875rem', color: '#7f1d1d', margin: 0 }}>
          This feature requires one of the following permissions: <strong>{roles.join(', ')}</strong>
        </p>
      </div>
    );
  }

  return <>{children}</>;
};

/**
 * Higher Order Component (HOC) version of RoleGuard
 */
export function withRoleGuard<P extends object>(
  Component: React.ComponentType<P>,
  allowedRoles: string[],
  fallback?: React.ReactNode,
): React.FC<P> {
  return function GuardedComponent(props: P) {
    return (
      <RoleGuard roles={allowedRoles} fallback={fallback}>
        <Component {...props} />
      </RoleGuard>
    );
  };
}

export default RoleGuard;
