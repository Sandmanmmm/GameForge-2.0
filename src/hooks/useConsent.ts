/**
 * React Hook for Consent Management
 * 
 * Provides easy-to-use React hooks for managing user consent state,
 * checking permissions, and handling consent updates.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { ConsentAPI, ConsentDecision, ConsentRecord, ConsentSummary } from '../services/consentAPI';

export interface UseConsentState {
  consents: ConsentSummary | null;
  isLoading: boolean;
  error: string | null;
  hasConsent: (consentType: string) => boolean;
  updateConsent: (consentType: string, value: boolean, notes?: string) => Promise<void>;
  bulkUpdateConsents: (decisions: ConsentDecision[]) => Promise<void>;
  revokeConsent: (consentType: string) => Promise<void>;
  refreshConsents: () => Promise<void>;
  exportData: () => Promise<void>;
}

/**
 * Main consent management hook
 */
export const useConsent = (): UseConsentState => {
  const [consents, setConsents] = useState<ConsentSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshConsents = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const summary = await ConsentAPI.getUserConsents();
      setConsents(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load consent information');
      console.error('Failed to refresh consents:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshConsents();
  }, [refreshConsents]);

  const hasConsent = useCallback((consentType: string): boolean => {
    if (!consents?.consents) return false;
    
    const consent = consents.consents.find(c => 
      c.consent_type === consentType && c.is_current
    );
    
    return consent?.consent_value || false;
  }, [consents]);

  const updateConsent = useCallback(async (
    consentType: string, 
    value: boolean, 
    notes?: string
  ): Promise<void> => {
    try {
      setError(null);
      await ConsentAPI.updateConsent(consentType, value, notes);
      await refreshConsents(); // Refresh to get updated state
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update consent');
      throw err; // Re-throw so component can handle it
    }
  }, [refreshConsents]);

  const bulkUpdateConsents = useCallback(async (
    decisions: ConsentDecision[]
  ): Promise<void> => {
    try {
      setError(null);
      const summary = await ConsentAPI.grantBulkConsent({ consents: decisions });
      setConsents(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update consents');
      throw err;
    }
  }, []);

  const revokeConsent = useCallback(async (consentType: string): Promise<void> => {
    try {
      setError(null);
      await ConsentAPI.revokeConsent(consentType);
      await refreshConsents();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke consent');
      throw err;
    }
  }, [refreshConsents]);

  const exportData = useCallback(async (): Promise<void> => {
    try {
      const blob = await ConsentAPI.exportConsentData();
      
      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `gameforge-consent-data-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export consent data');
      throw err;
    }
  }, []);

  return {
    consents,
    isLoading,
    error,
    hasConsent,
    updateConsent,
    bulkUpdateConsents,
    revokeConsent,
    refreshConsents,
    exportData
  };
};

/**
 * Hook for checking specific consent permissions
 */
export const useConsentCheck = (consentTypes: string[]) => {
  const [permissions, setPermissions] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkPermissions = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const perms = await ConsentAPI.hasConsents(consentTypes);
        setPermissions(perms);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to check consent permissions');
        console.error('Failed to check consent permissions:', err);
      } finally {
        setIsLoading(false);
      }
    };

    if (consentTypes.length > 0) {
      checkPermissions();
    }
  }, [consentTypes]);

  const hasPermission = useCallback((consentType: string): boolean => {
    return permissions[consentType] || false;
  }, [permissions]);

  const hasAllPermissions = useCallback((): boolean => {
    return consentTypes.every(type => permissions[type]);
  }, [consentTypes, permissions]);

  const hasAnyPermission = useCallback((): boolean => {
    return consentTypes.some(type => permissions[type]);
  }, [consentTypes, permissions]);

  return {
    permissions,
    isLoading,
    error,
    hasPermission,
    hasAllPermissions,
    hasAnyPermission
  };
};

/**
 * Hook for consent history
 */
export const useConsentHistory = (consentType: string) => {
  const [history, setHistory] = useState<ConsentRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadHistory = async () => {
      if (!consentType) return;

      try {
        setIsLoading(true);
        setError(null);
        const historyData = await ConsentAPI.getConsentHistory(consentType);
        setHistory(historyData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load consent history');
        console.error('Failed to load consent history:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadHistory();
  }, [consentType]);

  return {
    history,
    isLoading,
    error
  };
};

/**
 * Hook for consent types information
 */
export const useConsentTypes = () => {
  const [consentTypes, setConsentTypes] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadConsentTypes = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const types = await ConsentAPI.getConsentTypes();
        setConsentTypes(types);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load consent types');
        console.error('Failed to load consent types:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadConsentTypes();
  }, []);

  return {
    consentTypes,
    isLoading,
    error
  };
};

/**
 * Higher-order component for consent protection
 * Wraps components that require specific consent permissions
 */
export const withConsentProtection = (
  Component: React.ComponentType<any>,
  requiredConsents: string[],
  fallbackComponent?: React.ComponentType<any>
) => {
  return (props: any) => {
    const { hasAllPermissions, isLoading } = useConsentCheck(requiredConsents);

    if (isLoading) {
      return React.createElement('div', null, 'Checking permissions...');
    }

    if (!hasAllPermissions()) {
      if (fallbackComponent) {
        const FallbackComponent = fallbackComponent;
        return React.createElement(FallbackComponent, { ...props, requiredConsents });
      }
      return React.createElement(
        'div', 
        { className: "p-4 border border-amber-200 bg-amber-50 rounded-lg" },
        React.createElement('h3', { className: "font-medium text-amber-900 mb-2" }, 'Consent Required'),
        React.createElement(
          'p', 
          { className: "text-amber-700 text-sm" },
          `This feature requires additional consent permissions: ${requiredConsents.join(', ')}`
        )
      );
    }

    return React.createElement(Component, props);
  };
};

/**
 * Utility function to validate consent before performing an action
 */
export const useConsentGate = () => {
  const { hasConsent } = useConsent();

  return useCallback(async (
    consentType: string,
    action: () => Promise<void> | void,
    onConsentDenied?: () => void
  ): Promise<void> => {
    if (hasConsent(consentType)) {
      await action();
    } else if (onConsentDenied) {
      onConsentDenied();
    } else {
      throw new Error(`Consent required for: ${consentType}`);
    }
  }, [hasConsent]);
};

export default useConsent;