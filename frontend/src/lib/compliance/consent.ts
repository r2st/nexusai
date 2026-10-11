/**
 * GDPR Consent Management
 *
 * Handles user consent collection, storage, and withdrawal
 * in compliance with GDPR requirements.
 */

// Note: Audit logging disabled until backend API is available
// import { complianceAudit } from './audit';
import type { ConsentPurpose, ConsentRecord, ConsentPreferences } from './types';

// =============================================================================
// CONSENT CONFIGURATION
// =============================================================================

export const CONSENT_PURPOSES: Record<ConsentPurpose, {
  name: string;
  description: string;
  required: boolean;
  defaultValue: boolean;
}> = {
  essential: {
    name: 'Essential Cookies',
    description: 'Required for the platform to function properly. Cannot be disabled.',
    required: true,
    defaultValue: true,
  },
  analytics: {
    name: 'Analytics',
    description: 'Help us understand how you use our platform to improve it.',
    required: false,
    defaultValue: false,
  },
  marketing: {
    name: 'Marketing Communications',
    description: 'Receive updates about new features, tips, and promotional offers.',
    required: false,
    defaultValue: false,
  },
  personalization: {
    name: 'Personalization',
    description: 'Customize your experience based on your usage patterns.',
    required: false,
    defaultValue: false,
  },
  third_party: {
    name: 'Third-Party Services',
    description: 'Share data with integrated third-party services you connect.',
    required: false,
    defaultValue: false,
  },
  ai_training: {
    name: 'AI Model Training',
    description: 'Allow your anonymized data to improve our AI models.',
    required: false,
    defaultValue: false,
  },
  data_sharing: {
    name: 'Data Sharing',
    description: 'Share aggregated, anonymized data for research purposes.',
    required: false,
    defaultValue: false,
  },
};

export const CURRENT_PRIVACY_VERSION = '2.0.0';

// =============================================================================
// CONSENT STORAGE
// =============================================================================

const CONSENT_STORAGE_KEY = 'nexus_consent_preferences';
const CONSENT_VERSION_KEY = 'nexus_consent_version';

/**
 * Get stored consent preferences from localStorage
 */
export function getStoredConsent(): ConsentPreferences | null {
  if (typeof window === 'undefined') return null;

  try {
    const stored = localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!stored) return null;

    const preferences = JSON.parse(stored) as ConsentPreferences;

    // Check if consent version matches current privacy policy
    const storedVersion = localStorage.getItem(CONSENT_VERSION_KEY);
    if (storedVersion !== CURRENT_PRIVACY_VERSION) {
      // Consent needs to be re-collected due to policy change
      return null;
    }

    return preferences;
  } catch {
    return null;
  }
}

/**
 * Store consent preferences locally
 */
function storeConsent(preferences: ConsentPreferences): void {
  if (typeof window === 'undefined') return;

  localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(preferences));
  localStorage.setItem(CONSENT_VERSION_KEY, CURRENT_PRIVACY_VERSION);
}

/**
 * Clear stored consent (for withdrawal)
 */
export function clearStoredConsent(): void {
  if (typeof window === 'undefined') return;

  localStorage.removeItem(CONSENT_STORAGE_KEY);
  localStorage.removeItem(CONSENT_VERSION_KEY);
}

// =============================================================================
// CONSENT MANAGER CLASS
// =============================================================================

class ConsentManager {
  private preferences: ConsentPreferences | null = null;
  private listeners: ((preferences: ConsentPreferences) => void)[] = [];

  constructor() {
    this.preferences = getStoredConsent();
  }

  /**
   * Check if consent has been collected
   */
  hasConsent(): boolean {
    return this.preferences !== null;
  }

  /**
   * Get current consent preferences
   */
  getPreferences(): ConsentPreferences | null {
    return this.preferences;
  }

  /**
   * Check if a specific purpose is consented
   */
  hasConsentFor(purpose: ConsentPurpose): boolean {
    if (!this.preferences) {
      // Essential is always granted, others default to false
      return purpose === 'essential';
    }

    switch (purpose) {
      case 'essential':
        return true;
      case 'analytics':
        return this.preferences.analytics;
      case 'marketing':
        return this.preferences.marketing;
      case 'personalization':
        return this.preferences.personalization;
      case 'third_party':
        return this.preferences.thirdParty;
      case 'ai_training':
        return this.preferences.aiTraining;
      case 'data_sharing':
        return this.preferences.dataSharing;
      default:
        return false;
    }
  }

  /**
   * Set consent preferences
   */
  async setPreferences(preferences: Omit<ConsentPreferences, 'essential' | 'updatedAt'>): Promise<void> {
    const fullPreferences: ConsentPreferences = {
      essential: true, // Always required
      analytics: preferences.analytics,
      marketing: preferences.marketing,
      personalization: preferences.personalization,
      thirdParty: preferences.thirdParty,
      aiTraining: preferences.aiTraining,
      dataSharing: preferences.dataSharing,
      updatedAt: new Date().toISOString(),
    };

    // Store locally
    storeConsent(fullPreferences);
    this.preferences = fullPreferences;

    // Notify listeners
    this.notifyListeners();
  }

  /**
   * Accept all consent
   */
  async acceptAll(): Promise<void> {
    await this.setPreferences({
      analytics: true,
      marketing: true,
      personalization: true,
      thirdParty: true,
      aiTraining: true,
      dataSharing: true,
    });
  }

  /**
   * Reject all optional consent (keep essential only)
   */
  async rejectAll(): Promise<void> {
    await this.setPreferences({
      analytics: false,
      marketing: false,
      personalization: false,
      thirdParty: false,
      aiTraining: false,
      dataSharing: false,
    });
  }

  /**
   * Withdraw specific consent
   */
  async withdrawConsent(purpose: ConsentPurpose): Promise<void> {
    if (purpose === 'essential') {
      throw new Error('Cannot withdraw consent for essential functionality');
    }

    if (!this.preferences) return;

    const updated = { ...this.preferences };

    switch (purpose) {
      case 'analytics':
        updated.analytics = false;
        break;
      case 'marketing':
        updated.marketing = false;
        break;
      case 'personalization':
        updated.personalization = false;
        break;
      case 'third_party':
        updated.thirdParty = false;
        break;
      case 'ai_training':
        updated.aiTraining = false;
        break;
      case 'data_sharing':
        updated.dataSharing = false;
        break;
    }

    updated.updatedAt = new Date().toISOString();

    storeConsent(updated);
    this.preferences = updated;

    this.notifyListeners();
  }

  /**
   * Subscribe to consent changes
   */
  subscribe(listener: (preferences: ConsentPreferences) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notifyListeners(): void {
    if (this.preferences) {
      this.listeners.forEach(listener => listener(this.preferences!));
    }
  }

  /**
   * Get consent history from the backend API.
   * Returns empty array if the endpoint is unavailable.
   */
  async getConsentHistory(): Promise<ConsentRecord[]> {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
      const res = await fetch(`${apiBase}/api/v1/compliance/consent/history`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  }
}

// Singleton instance
export const consentManager = new ConsentManager();

// =============================================================================
// CONSENT HOOKS
// =============================================================================

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook to access consent state
 */
export function useConsent() {
  const [preferences, setPreferences] = useState<ConsentPreferences | null>(
    consentManager.getPreferences()
  );
  const [needsConsent, setNeedsConsent] = useState(!consentManager.hasConsent());

  useEffect(() => {
    const unsubscribe = consentManager.subscribe(setPreferences);
    return unsubscribe;
  }, []);

  const hasConsentFor = useCallback(
    (purpose: ConsentPurpose) => consentManager.hasConsentFor(purpose),
    [preferences]
  );

  const updatePreferences = useCallback(
    async (newPreferences: Omit<ConsentPreferences, 'essential' | 'updatedAt'>) => {
      await consentManager.setPreferences(newPreferences);
      setNeedsConsent(false);
    },
    []
  );

  const acceptAll = useCallback(async () => {
    await consentManager.acceptAll();
    setNeedsConsent(false);
  }, []);

  const rejectAll = useCallback(async () => {
    await consentManager.rejectAll();
    setNeedsConsent(false);
  }, []);

  const withdrawConsent = useCallback(async (purpose: ConsentPurpose) => {
    await consentManager.withdrawConsent(purpose);
  }, []);

  return {
    preferences,
    needsConsent,
    hasConsentFor,
    updatePreferences,
    acceptAll,
    rejectAll,
    withdrawConsent,
  };
}

/**
 * Hook to check if analytics is allowed
 */
export function useAnalyticsConsent(): boolean {
  const { hasConsentFor } = useConsent();
  return hasConsentFor('analytics');
}

/**
 * Hook to check if marketing is allowed
 */
export function useMarketingConsent(): boolean {
  const { hasConsentFor } = useConsent();
  return hasConsentFor('marketing');
}

// =============================================================================
// CONSENT UTILITIES
// =============================================================================

/**
 * Execute callback only if consent is given
 */
export function withConsent<T>(
  purpose: ConsentPurpose,
  callback: () => T,
  fallback?: T
): T | undefined {
  if (consentManager.hasConsentFor(purpose)) {
    return callback();
  }
  return fallback;
}

/**
 * Conditionally load analytics scripts
 */
export function loadAnalyticsIfConsented(): void {
  if (!consentManager.hasConsentFor('analytics')) return;

  // Load analytics scripts here
  // Example: Google Analytics, Mixpanel, etc.
}

/**
 * Check if data processing is allowed
 */
export function canProcessData(purposes: ConsentPurpose[]): boolean {
  return purposes.every(purpose => consentManager.hasConsentFor(purpose));
}

/**
 * Get consent status summary
 */
export function getConsentSummary(): Record<ConsentPurpose, boolean> {
  return {
    essential: true,
    analytics: consentManager.hasConsentFor('analytics'),
    marketing: consentManager.hasConsentFor('marketing'),
    personalization: consentManager.hasConsentFor('personalization'),
    third_party: consentManager.hasConsentFor('third_party'),
    ai_training: consentManager.hasConsentFor('ai_training'),
    data_sharing: consentManager.hasConsentFor('data_sharing'),
  };
}
