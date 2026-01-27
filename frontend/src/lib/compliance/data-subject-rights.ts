/**
 * GDPR Data Subject Rights (DSR) Management
 *
 * Handles data subject requests including:
 * - Right of Access (Article 15)
 * - Right to Rectification (Article 16)
 * - Right to Erasure (Article 17)
 * - Right to Restriction (Article 18)
 * - Right to Data Portability (Article 20)
 * - Right to Object (Article 21)
 */

import { api } from '@/lib/api';
import { complianceAudit } from './audit';
import type { DSRType, DSRStatus, DataSubjectRequest } from './types';

// =============================================================================
// DSR CONFIGURATION
// =============================================================================

export const DSR_CONFIG: Record<DSRType, {
  name: string;
  description: string;
  gdprArticle: string;
  deadline: number; // Days to complete
  requiresVerification: boolean;
}> = {
  access: {
    name: 'Right of Access',
    description: 'Request a copy of all personal data we hold about you.',
    gdprArticle: 'Article 15',
    deadline: 30,
    requiresVerification: true,
  },
  rectification: {
    name: 'Right to Rectification',
    description: 'Request correction of inaccurate personal data.',
    gdprArticle: 'Article 16',
    deadline: 30,
    requiresVerification: true,
  },
  erasure: {
    name: 'Right to Erasure',
    description: 'Request deletion of your personal data ("right to be forgotten").',
    gdprArticle: 'Article 17',
    deadline: 30,
    requiresVerification: true,
  },
  restriction: {
    name: 'Right to Restriction',
    description: 'Request restriction of processing of your personal data.',
    gdprArticle: 'Article 18',
    deadline: 30,
    requiresVerification: true,
  },
  portability: {
    name: 'Right to Data Portability',
    description: 'Receive your data in a structured, machine-readable format.',
    gdprArticle: 'Article 20',
    deadline: 30,
    requiresVerification: true,
  },
  objection: {
    name: 'Right to Object',
    description: 'Object to processing of your personal data.',
    gdprArticle: 'Article 21',
    deadline: 30,
    requiresVerification: false,
  },
};

// =============================================================================
// DSR SERVICE
// =============================================================================

class DataSubjectRightsService {
  /**
   * Submit a new data subject request
   */
  async submitRequest(
    type: DSRType,
    reason?: string,
    additionalInfo?: Record<string, unknown>
  ): Promise<DataSubjectRequest> {
    try {
      const response = await api.post('/compliance/dsr', {
        type,
        reason,
        additionalInfo,
      });

      const request = response.data as DataSubjectRequest;

      // Log the submission
      complianceAudit.dsrSubmitted(type, request.id);

      return request;
    } catch (error) {
      console.error('Failed to submit DSR:', error);
      throw error;
    }
  }

  /**
   * Get all DSR requests for the current user
   */
  async getMyRequests(): Promise<DataSubjectRequest[]> {
    try {
      const response = await api.get('/compliance/dsr/my-requests');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch DSR requests:', error);
      return [];
    }
  }

  /**
   * Get a specific DSR request by ID
   */
  async getRequest(requestId: string): Promise<DataSubjectRequest | null> {
    try {
      const response = await api.get(`/compliance/dsr/${requestId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch DSR request:', error);
      return null;
    }
  }

  /**
   * Cancel a pending DSR request
   */
  async cancelRequest(requestId: string): Promise<void> {
    try {
      await api.delete(`/compliance/dsr/${requestId}`);
    } catch (error) {
      console.error('Failed to cancel DSR request:', error);
      throw error;
    }
  }

  /**
   * Download data export (for access/portability requests)
   */
  async downloadExport(requestId: string): Promise<Blob> {
    try {
      const response = await api.get(`/compliance/dsr/${requestId}/download`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      console.error('Failed to download export:', error);
      throw error;
    }
  }

  /**
   * Verify identity for DSR request
   */
  async verifyIdentity(
    requestId: string,
    verificationCode: string
  ): Promise<boolean> {
    try {
      const response = await api.post(`/compliance/dsr/${requestId}/verify`, {
        code: verificationCode,
      });
      return response.data.verified;
    } catch (error) {
      console.error('Failed to verify identity:', error);
      return false;
    }
  }

  /**
   * Request data deletion (Article 17)
   */
  async requestDeletion(
    dataCategories?: string[],
    reason?: string
  ): Promise<DataSubjectRequest> {
    return this.submitRequest('erasure', reason, { dataCategories });
  }

  /**
   * Request data export (Article 20)
   */
  async requestDataExport(
    format: 'json' | 'csv' = 'json',
    dataCategories?: string[]
  ): Promise<DataSubjectRequest> {
    return this.submitRequest('portability', undefined, { format, dataCategories });
  }

  /**
   * Request data access (Article 15)
   */
  async requestDataAccess(): Promise<DataSubjectRequest> {
    return this.submitRequest('access');
  }

  /**
   * Object to processing (Article 21)
   */
  async objectToProcessing(
    processingType: string,
    reason: string
  ): Promise<DataSubjectRequest> {
    return this.submitRequest('objection', reason, { processingType });
  }

  /**
   * Request data rectification (Article 16)
   */
  async requestRectification(
    corrections: Record<string, unknown>,
    reason?: string
  ): Promise<DataSubjectRequest> {
    return this.submitRequest('rectification', reason, { corrections });
  }

  /**
   * Get data categories available for export
   */
  async getDataCategories(): Promise<string[]> {
    try {
      const response = await api.get('/compliance/dsr/data-categories');
      return response.data;
    } catch {
      // Return default categories if API fails
      return [
        'profile',
        'conversations',
        'documents',
        'activity_logs',
        'preferences',
        'integrations',
      ];
    }
  }
}

// Singleton instance
export const dsrService = new DataSubjectRightsService();

// =============================================================================
// DSR HOOKS
// =============================================================================

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook to manage DSR requests
 */
export function useDataSubjectRights() {
  const [requests, setRequests] = useState<DataSubjectRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await dsrService.getMyRequests();
      setRequests(data);
    } catch (err) {
      setError('Failed to load requests');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const submitRequest = useCallback(
    async (type: DSRType, reason?: string) => {
      setLoading(true);
      setError(null);
      try {
        const request = await dsrService.submitRequest(type, reason);
        setRequests(prev => [request, ...prev]);
        return request;
      } catch (err) {
        setError('Failed to submit request');
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const cancelRequest = useCallback(async (requestId: string) => {
    try {
      await dsrService.cancelRequest(requestId);
      setRequests(prev => prev.filter(r => r.id !== requestId));
    } catch (err) {
      setError('Failed to cancel request');
      throw err;
    }
  }, []);

  const downloadExport = useCallback(async (requestId: string) => {
    try {
      const blob = await dsrService.downloadExport(requestId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `data-export-${requestId}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download export');
      throw err;
    }
  }, []);

  return {
    requests,
    loading,
    error,
    submitRequest,
    cancelRequest,
    downloadExport,
    refreshRequests: fetchRequests,
  };
}

/**
 * Hook for quick data deletion request
 */
export function useDataDeletion() {
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestDeletion = useCallback(
    async (dataCategories?: string[], reason?: string) => {
      setSubmitting(true);
      setError(null);
      try {
        await dsrService.requestDeletion(dataCategories, reason);
        setSubmitted(true);
      } catch (err) {
        setError('Failed to submit deletion request');
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  return {
    requestDeletion,
    submitting,
    submitted,
    error,
  };
}

/**
 * Hook for data export request
 */
export function useDataExport() {
  const [submitting, setSubmitting] = useState(false);
  const [request, setRequest] = useState<DataSubjectRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  const requestExport = useCallback(
    async (format: 'json' | 'csv' = 'json', dataCategories?: string[]) => {
      setSubmitting(true);
      setError(null);
      try {
        const result = await dsrService.requestDataExport(format, dataCategories);
        setRequest(result);
        return result;
      } catch (err) {
        setError('Failed to submit export request');
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  return {
    requestExport,
    submitting,
    request,
    error,
  };
}

// =============================================================================
// DSR STATUS HELPERS
// =============================================================================

/**
 * Get human-readable status label
 */
export function getDSRStatusLabel(status: DSRStatus): string {
  switch (status) {
    case 'pending':
      return 'Pending Review';
    case 'in_progress':
      return 'In Progress';
    case 'completed':
      return 'Completed';
    case 'rejected':
      return 'Rejected';
    case 'expired':
      return 'Expired';
    default:
      return 'Unknown';
  }
}

/**
 * Get status color for UI
 */
export function getDSRStatusColor(status: DSRStatus): string {
  switch (status) {
    case 'pending':
      return 'yellow';
    case 'in_progress':
      return 'blue';
    case 'completed':
      return 'green';
    case 'rejected':
      return 'red';
    case 'expired':
      return 'gray';
    default:
      return 'gray';
  }
}

/**
 * Calculate days remaining for DSR deadline
 */
export function getDaysRemaining(request: DataSubjectRequest): number {
  const dueDate = new Date(request.dueDate);
  const now = new Date();
  const diffTime = dueDate.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(0, diffDays);
}

/**
 * Check if DSR is overdue
 */
export function isDSROverdue(request: DataSubjectRequest): boolean {
  if (request.status === 'completed' || request.status === 'rejected') {
    return false;
  }
  return getDaysRemaining(request) === 0;
}
