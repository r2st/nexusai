/**
 * Data Retention Policy Management
 *
 * Implements data retention policies for SOC2, HIPAA, and GDPR compliance.
 * Handles data lifecycle management, archival, and deletion.
 */

import { api } from '@/lib/api';
import { dataAudit } from './audit';
import type { RetentionPolicy, ComplianceFramework } from './types';

// =============================================================================
// RETENTION POLICY DEFINITIONS
// =============================================================================

export const RETENTION_POLICIES: RetentionPolicy[] = [
  // User Data
  {
    id: 'user_account',
    dataCategory: 'User Account Data',
    description: 'Basic user profile, authentication, and account settings',
    retentionPeriod: 365 * 3, // 3 years after account closure
    legalBasis: 'Contract fulfillment, legal obligation (tax records)',
    framework: ['SOC2', 'GDPR', 'HIPAA'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'user_preferences',
    dataCategory: 'User Preferences',
    description: 'UI preferences, notification settings, customizations',
    retentionPeriod: 0, // Delete immediately on account closure
    legalBasis: 'Consent',
    framework: ['GDPR'],
    autoDelete: true,
    reviewRequired: false,
  },

  // Communication Data
  {
    id: 'chat_conversations',
    dataCategory: 'Chat Conversations',
    description: 'AI chat messages and conversation history',
    retentionPeriod: 365, // 1 year
    legalBasis: 'Contract fulfillment, legitimate interest',
    framework: ['GDPR', 'SOC2'],
    autoDelete: true,
    reviewRequired: false,
  },
  {
    id: 'support_tickets',
    dataCategory: 'Support Tickets',
    description: 'Customer support communications',
    retentionPeriod: 365 * 3, // 3 years
    legalBasis: 'Contract fulfillment, legitimate interest',
    framework: ['SOC2', 'GDPR'],
    autoDelete: false,
    reviewRequired: true,
  },

  // Security & Audit
  {
    id: 'audit_logs',
    dataCategory: 'Audit Logs',
    description: 'Security events, access logs, compliance audit trail',
    retentionPeriod: 365 * 7, // 7 years (SOC2/HIPAA requirement)
    legalBasis: 'Legal obligation, legitimate interest',
    framework: ['SOC2', 'HIPAA'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'security_events',
    dataCategory: 'Security Events',
    description: 'Login attempts, MFA events, suspicious activity',
    retentionPeriod: 365 * 2, // 2 years
    legalBasis: 'Legitimate interest (security)',
    framework: ['SOC2', 'HIPAA'],
    autoDelete: true,
    reviewRequired: false,
  },
  {
    id: 'session_data',
    dataCategory: 'Session Data',
    description: 'Active sessions, session tokens, device info',
    retentionPeriod: 90, // 90 days
    legalBasis: 'Contract fulfillment, legitimate interest',
    framework: ['SOC2', 'GDPR'],
    autoDelete: true,
    reviewRequired: false,
  },

  // Documents & Files
  {
    id: 'uploaded_documents',
    dataCategory: 'Uploaded Documents',
    description: 'User-uploaded files and documents',
    retentionPeriod: 365 * 2, // 2 years
    legalBasis: 'Contract fulfillment',
    framework: ['SOC2', 'GDPR'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'document_vectors',
    dataCategory: 'Document Embeddings',
    description: 'Vector embeddings for document search',
    retentionPeriod: 0, // Delete with source document
    legalBasis: 'Contract fulfillment',
    framework: ['SOC2'],
    autoDelete: true,
    reviewRequired: false,
  },

  // Analytics
  {
    id: 'usage_analytics',
    dataCategory: 'Usage Analytics',
    description: 'Aggregated usage statistics and metrics',
    retentionPeriod: 365 * 2, // 2 years
    legalBasis: 'Legitimate interest',
    framework: ['GDPR'],
    autoDelete: true,
    reviewRequired: false,
  },
  {
    id: 'performance_metrics',
    dataCategory: 'Performance Metrics',
    description: 'System performance and error tracking',
    retentionPeriod: 365, // 1 year
    legalBasis: 'Legitimate interest',
    framework: ['SOC2'],
    autoDelete: true,
    reviewRequired: false,
  },

  // HIPAA-Specific
  {
    id: 'phi_data',
    dataCategory: 'Protected Health Information',
    description: 'Any health-related data processed through the system',
    retentionPeriod: 365 * 6, // 6 years (HIPAA minimum)
    legalBasis: 'HIPAA requirement (45 CFR 164.530)',
    framework: ['HIPAA'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'hipaa_authorizations',
    dataCategory: 'HIPAA Authorizations',
    description: 'Signed authorizations for PHI disclosure',
    retentionPeriod: 365 * 6, // 6 years
    legalBasis: 'HIPAA requirement',
    framework: ['HIPAA'],
    autoDelete: false,
    reviewRequired: true,
  },

  // Billing & Financial
  {
    id: 'billing_records',
    dataCategory: 'Billing Records',
    description: 'Invoices, payment history, subscription data',
    retentionPeriod: 365 * 7, // 7 years (tax requirements)
    legalBasis: 'Legal obligation (tax records)',
    framework: ['SOC2', 'GDPR'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'payment_methods',
    dataCategory: 'Payment Methods',
    description: 'Stored payment method tokens (not actual card data)',
    retentionPeriod: 0, // Delete immediately when removed
    legalBasis: 'Consent',
    framework: ['SOC2', 'GDPR'],
    autoDelete: true,
    reviewRequired: false,
  },

  // Compliance Records
  {
    id: 'consent_records',
    dataCategory: 'Consent Records',
    description: 'GDPR consent grants and withdrawals',
    retentionPeriod: 365 * 7, // 7 years
    legalBasis: 'Legal obligation (GDPR compliance)',
    framework: ['GDPR'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'dsr_records',
    dataCategory: 'Data Subject Requests',
    description: 'GDPR data subject request records',
    retentionPeriod: 365 * 7, // 7 years
    legalBasis: 'Legal obligation (GDPR compliance)',
    framework: ['GDPR'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'breach_records',
    dataCategory: 'Breach Records',
    description: 'Data breach documentation and notifications',
    retentionPeriod: 365 * 7, // 7 years
    legalBasis: 'Legal obligation',
    framework: ['SOC2', 'HIPAA', 'GDPR'],
    autoDelete: false,
    reviewRequired: true,
  },

  // API & Integration
  {
    id: 'api_keys',
    dataCategory: 'API Keys',
    description: 'API authentication keys and tokens',
    retentionPeriod: 365, // 1 year after revocation
    legalBasis: 'Contract fulfillment',
    framework: ['SOC2'],
    autoDelete: true,
    reviewRequired: false,
  },
  {
    id: 'integration_credentials',
    dataCategory: 'Integration Credentials',
    description: 'Third-party integration authentication data',
    retentionPeriod: 0, // Delete immediately when disconnected
    legalBasis: 'Consent',
    framework: ['SOC2', 'GDPR'],
    autoDelete: true,
    reviewRequired: false,
  },
];

// =============================================================================
// RETENTION SERVICE
// =============================================================================

class RetentionService {
  /**
   * Get all retention policies
   */
  getPolicies(): RetentionPolicy[] {
    return RETENTION_POLICIES;
  }

  /**
   * Get policies by framework
   */
  getPoliciesByFramework(framework: ComplianceFramework): RetentionPolicy[] {
    return RETENTION_POLICIES.filter(p => p.framework.includes(framework));
  }

  /**
   * Get policy for a specific data category
   */
  getPolicy(categoryId: string): RetentionPolicy | undefined {
    return RETENTION_POLICIES.find(p => p.id === categoryId);
  }

  /**
   * Calculate expiration date for data
   */
  calculateExpirationDate(
    categoryId: string,
    createdAt: Date = new Date()
  ): Date | null {
    const policy = this.getPolicy(categoryId);
    if (!policy || policy.retentionPeriod === 0) return null;

    const expirationDate = new Date(createdAt);
    expirationDate.setDate(expirationDate.getDate() + policy.retentionPeriod);
    return expirationDate;
  }

  /**
   * Check if data should be retained
   */
  shouldRetain(categoryId: string, createdAt: Date): boolean {
    const expirationDate = this.calculateExpirationDate(categoryId, createdAt);
    if (!expirationDate) return true; // No expiration

    return new Date() < expirationDate;
  }

  /**
   * Get data pending deletion
   */
  async getPendingDeletions(): Promise<{
    category: string;
    count: number;
    oldestDate: string;
  }[]> {
    try {
      const response = await api.get('/compliance/retention/pending-deletions');
      return response.data;
    } catch {
      return [];
    }
  }

  /**
   * Execute data retention cleanup
   */
  async executeRetentionCleanup(
    categoryId: string,
    dryRun: boolean = true
  ): Promise<{
    affected: number;
    deleted: number;
    errors: string[];
  }> {
    try {
      const response = await api.post('/compliance/retention/cleanup', {
        categoryId,
        dryRun,
      });

      if (!dryRun) {
        dataAudit.deleted(categoryId, 'retention-cleanup', 'Automated retention policy');
      }

      return response.data;
    } catch (error) {
      console.error('Retention cleanup failed:', error);
      throw error;
    }
  }

  /**
   * Request manual data deletion
   */
  async requestManualDeletion(
    categoryId: string,
    resourceIds: string[],
    reason: string
  ): Promise<void> {
    try {
      await api.post('/compliance/retention/manual-delete', {
        categoryId,
        resourceIds,
        reason,
      });

      for (const id of resourceIds) {
        dataAudit.deleted(categoryId, id, reason);
      }
    } catch (error) {
      console.error('Manual deletion request failed:', error);
      throw error;
    }
  }

  /**
   * Extend retention for specific data
   */
  async extendRetention(
    categoryId: string,
    resourceIds: string[],
    extensionDays: number,
    reason: string
  ): Promise<void> {
    try {
      await api.post('/compliance/retention/extend', {
        categoryId,
        resourceIds,
        extensionDays,
        reason,
      });
    } catch (error) {
      console.error('Retention extension failed:', error);
      throw error;
    }
  }

  /**
   * Apply legal hold to prevent deletion
   */
  async applyLegalHold(
    resourceType: string,
    resourceIds: string[],
    holdReason: string,
    holdUntil?: Date
  ): Promise<void> {
    try {
      await api.post('/compliance/retention/legal-hold', {
        resourceType,
        resourceIds,
        holdReason,
        holdUntil: holdUntil?.toISOString(),
      });
    } catch (error) {
      console.error('Legal hold application failed:', error);
      throw error;
    }
  }

  /**
   * Remove legal hold
   */
  async removeLegalHold(
    resourceType: string,
    resourceIds: string[],
    reason: string
  ): Promise<void> {
    try {
      await api.post('/compliance/retention/remove-legal-hold', {
        resourceType,
        resourceIds,
        reason,
      });
    } catch (error) {
      console.error('Legal hold removal failed:', error);
      throw error;
    }
  }

  /**
   * Get retention report
   */
  async getRetentionReport(): Promise<{
    totalRecords: number;
    byCategory: Record<string, {
      count: number;
      pendingDeletion: number;
      legalHold: number;
    }>;
    upcomingDeletions: {
      date: string;
      category: string;
      count: number;
    }[];
  }> {
    try {
      const response = await api.get('/compliance/retention/report');
      return response.data;
    } catch {
      return {
        totalRecords: 0,
        byCategory: {},
        upcomingDeletions: [],
      };
    }
  }
}

// Singleton instance
export const retentionService = new RetentionService();

// =============================================================================
// RETENTION HOOKS
// =============================================================================

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook for retention policy management
 */
export function useRetentionPolicies() {
  const [policies] = useState<RetentionPolicy[]>(retentionService.getPolicies());

  const getPoliciesByFramework = useCallback(
    (framework: ComplianceFramework) => retentionService.getPoliciesByFramework(framework),
    []
  );

  const getPolicy = useCallback(
    (categoryId: string) => retentionService.getPolicy(categoryId),
    []
  );

  return {
    policies,
    getPoliciesByFramework,
    getPolicy,
  };
}

/**
 * Hook for retention cleanup
 */
export function useRetentionCleanup() {
  const [pendingDeletions, setPendingDeletions] = useState<{
    category: string;
    count: number;
    oldestDate: string;
  }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPendingDeletions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await retentionService.getPendingDeletions();
      setPendingDeletions(data);
    } catch {
      setError('Failed to fetch pending deletions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPendingDeletions();
  }, [fetchPendingDeletions]);

  const executeCleanup = useCallback(
    async (categoryId: string, dryRun: boolean = true) => {
      setLoading(true);
      setError(null);
      try {
        const result = await retentionService.executeRetentionCleanup(categoryId, dryRun);
        if (!dryRun) {
          await fetchPendingDeletions();
        }
        return result;
      } catch {
        setError('Cleanup execution failed');
        throw new Error('Cleanup execution failed');
      } finally {
        setLoading(false);
      }
    },
    [fetchPendingDeletions]
  );

  return {
    pendingDeletions,
    loading,
    error,
    executeCleanup,
    refresh: fetchPendingDeletions,
  };
}

// =============================================================================
// RETENTION UTILITIES
// =============================================================================

/**
 * Format retention period for display
 */
export function formatRetentionPeriod(days: number): string {
  if (days === 0) return 'Immediate deletion';
  if (days < 30) return `${days} days`;
  if (days < 365) return `${Math.round(days / 30)} months`;
  return `${Math.round(days / 365)} years`;
}

/**
 * Get days until data expires
 */
export function getDaysUntilExpiration(
  categoryId: string,
  createdAt: Date
): number | null {
  const expirationDate = retentionService.calculateExpirationDate(categoryId, createdAt);
  if (!expirationDate) return null;

  const now = new Date();
  const diffTime = expirationDate.getTime() - now.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Check if data is under legal hold
 */
export async function isUnderLegalHold(
  resourceType: string,
  resourceId: string
): Promise<boolean> {
  try {
    const response = await api.get(
      `/compliance/retention/legal-hold-status/${resourceType}/${resourceId}`
    );
    return response.data.underHold;
  } catch {
    return false;
  }
}
