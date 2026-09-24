/**
 * FLIP v3.0 — useAuth Hook (Segment 01)
 * Accesses authentication context, tokens, roles, and profile synchronization.
 */

import { useContext } from 'react';
import { AuthContext, type AuthContextType } from './AuthProvider';

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an <AuthProvider>');
  }
  return context;
}

export default useAuth;
