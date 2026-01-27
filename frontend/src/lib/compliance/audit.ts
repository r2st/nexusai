/**
 * Compliance Audit Logging System
 *
 * Provides comprehensive audit logging for SOC2, HIPAA, and GDPR compliance.
 * Captures security events, data access, and compliance-relevant activities.
 */

import { api } from '@/lib/api';

// =============================================================================
// AUDIT EVENT TYPES
// =============================================================================

export type AuditCategory =
  | 'authentication'
  | 'authorization'
  | 'data_access'
  | 'data_modification'
  | 'data_deletion'
  | 'data_export'
  | 'configuration'
  | 'security'
  | 'compliance'
  | 'system';

export type AuditSeverity = 'info' | 'warning' | 'error' | 'critical';

export type AuditAction =
  // Authentication
  | 'user_login'
  | 'user_logout'
  | 'login_failed'
  | 'mfa_enabled'
  | 'mfa_disabled'
  | 'mfa_challenge'
  | 'password_changed'
  | 'password_reset_requested'
  | 'password_reset_completed'
  | 'session_created'
  | 'session_terminated'
  | 'session_expired'
  // Authorization
  | 'permission_granted'
  | 'permission_revoked'
  | 'role_assigned'
  | 'role_removed'
  | 'access_denied'
  // Data Access (HIPAA/GDPR critical)
  | 'data_viewed'
  | 'data_searched'
  | 'data_exported'
  | 'data_printed'
  | 'phi_accessed'
  | 'pii_accessed'
  // Data Modification
  | 'data_created'
  | 'data_updated'
  | 'data_deleted'
  | 'bulk_operation'
  // Compliance
  | 'consent_given'
  | 'consent_withdrawn'
  | 'dsr_submitted'
  | 'dsr_completed'
  | 'data_retention_applied'
  | 'data_anonymized'
  | 'breach_detected'
  | 'breach_reported'
  // Security
  | 'suspicious_activity'
  | 'rate_limit_exceeded'
  | 'invalid_input_detected'
  | 'encryption_key_rotated'
  | 'security_alert'
  // Configuration
  | 'setting_changed'
  | 'integration_added'
  | 'integration_removed'
  | 'api_key_created'
  | 'api_key_revoked'
  // System
  | 'system_startup'
  | 'system_shutdown'
  | 'backup_created'
  | 'backup_restored';

export interface AuditEvent {
  id?: string;
  timestamp: string;
  category: AuditCategory;
  action: AuditAction;
  severity: AuditSeverity;
  actor: {
    userId?: string;
    email?: string;
    role?: string;
    ipAddress?: string;
    userAgent?: string;
    sessionId?: string;
  };
  resource: {
    type: string;
    id?: string;
    name?: string;
  };
  details: Record<string, unknown>;
  outcome: 'success' | 'failure' | 'partial';
  errorMessage?: string;
  // Compliance metadata
  compliance: {
    frameworks: ('SOC2' | 'HIPAA' | 'GDPR')[];
    dataClassification?: 'public' | 'internal' | 'confidential' | 'restricted';
    containsPHI?: boolean;
    containsPII?: boolean;
    retentionDays: number;
  };
}

// =============================================================================
// AUDIT LOGGER CLASS
// =============================================================================

class AuditLogger {
  private queue: AuditEvent[] = [];
  private flushInterval: ReturnType<typeof setInterval> | null = null;
  private readonly FLUSH_INTERVAL_MS = 5000;
  private readonly MAX_QUEUE_SIZE = 50;

  constructor() {
    if (typeof window !== 'undefined') {
      this.startFlushInterval();
      window.addEventListener('beforeunload', () => this.flush());
    }
  }

  private startFlushInterval(): void {
    this.flushInterval = setInterval(() => {
      if (this.queue.length > 0) {
        this.flush();
      }
    }, this.FLUSH_INTERVAL_MS);
  }

  /**
   * Log an audit event
   */
  async log(event: Omit<AuditEvent, 'id' | 'timestamp'>): Promise<void> {
    const fullEvent: AuditEvent = {
      ...event,
      timestamp: new Date().toISOString(),
      actor: {
        ...event.actor,
        ipAddress: event.actor.ipAddress || this.getClientIP(),
        userAgent: event.actor.userAgent || (typeof navigator !== 'undefined' ? navigator.userAgent : undefined),
      },
    };

    // Add to queue
    this.queue.push(fullEvent);

    // Critical events should be logged immediately
    if (event.severity === 'critical' || event.severity === 'error') {
      await this.flush();
    } else if (this.queue.length >= this.MAX_QUEUE_SIZE) {
      await this.flush();
    }

    // Also log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[AUDIT]', fullEvent);
    }
  }

  /**
   * Flush queued events to the server
   */
  async flush(): Promise<void> {
    if (this.queue.length === 0) return;

    const eventsToSend = [...this.queue];
    this.queue = [];

    try {
      await api.post('/compliance/audit-logs', { events: eventsToSend });
    } catch (error) {
      // Re-queue failed events
      this.queue = [...eventsToSend, ...this.queue];
      console.error('[AUDIT] Failed to send audit logs:', error);
    }
  }

  private getClientIP(): string | undefined {
    // IP is typically captured server-side
    return undefined;
  }

  /**
   * Stop the flush interval
   */
  destroy(): void {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }
    this.flush();
  }
}

// Singleton instance
export const auditLogger = new AuditLogger();

// =============================================================================
// CONVENIENCE LOGGING FUNCTIONS
// =============================================================================

interface LogOptions {
  userId?: string;
  email?: string;
  role?: string;
  sessionId?: string;
}

/**
 * Get current user context from auth store
 */
function getCurrentUserContext(): LogOptions {
  if (typeof window === 'undefined') return {};

  try {
    const authData = localStorage.getItem('auth-storage');
    if (authData) {
      const parsed = JSON.parse(authData);
      return {
        userId: parsed.state?.user?.id,
        email: parsed.state?.user?.email,
        role: parsed.state?.user?.role,
      };
    }
  } catch {
    // Ignore parsing errors
  }
  return {};
}

/**
 * Log authentication events
 */
export const authAudit = {
  login: (success: boolean, email: string, reason?: string) =>
    auditLogger.log({
      category: 'authentication',
      action: success ? 'user_login' : 'login_failed',
      severity: success ? 'info' : 'warning',
      actor: { email },
      resource: { type: 'session' },
      details: { reason },
      outcome: success ? 'success' : 'failure',
      errorMessage: success ? undefined : reason,
      compliance: {
        frameworks: ['SOC2', 'HIPAA', 'GDPR'],
        retentionDays: 365 * 7,
      },
    }),

  logout: (options: LogOptions = {}) =>
    auditLogger.log({
      category: 'authentication',
      action: 'user_logout',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'session' },
      details: {},
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365,
      },
    }),

  mfaEnabled: (options: LogOptions = {}) =>
    auditLogger.log({
      category: 'authentication',
      action: 'mfa_enabled',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'user_security' },
      details: {},
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA'],
        retentionDays: 365 * 7,
      },
    }),

  mfaDisabled: (options: LogOptions = {}) =>
    auditLogger.log({
      category: 'authentication',
      action: 'mfa_disabled',
      severity: 'warning',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'user_security' },
      details: {},
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA'],
        retentionDays: 365 * 7,
      },
    }),

  passwordChanged: (options: LogOptions = {}) =>
    auditLogger.log({
      category: 'authentication',
      action: 'password_changed',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'user_credentials' },
      details: {},
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA'],
        retentionDays: 365 * 7,
      },
    }),

  sessionTerminated: (sessionId: string, reason: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'authentication',
      action: 'session_terminated',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'session', id: sessionId },
      details: { reason },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365,
      },
    }),
};

/**
 * Log data access events (critical for HIPAA)
 */
export const dataAudit = {
  accessed: (
    resourceType: string,
    resourceId: string,
    containsPHI: boolean = false,
    containsPII: boolean = false,
    options: LogOptions = {}
  ) =>
    auditLogger.log({
      category: 'data_access',
      action: containsPHI ? 'phi_accessed' : containsPII ? 'pii_accessed' : 'data_viewed',
      severity: containsPHI ? 'warning' : 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: resourceType, id: resourceId },
      details: { containsPHI, containsPII },
      outcome: 'success',
      compliance: {
        frameworks: containsPHI ? ['HIPAA', 'SOC2'] : containsPII ? ['GDPR', 'SOC2'] : ['SOC2'],
        dataClassification: containsPHI ? 'restricted' : containsPII ? 'confidential' : 'internal',
        containsPHI,
        containsPII,
        retentionDays: containsPHI ? 365 * 6 : 365 * 7,
      },
    }),

  exported: (
    resourceType: string,
    resourceId: string,
    format: string,
    recordCount: number,
    options: LogOptions = {}
  ) =>
    auditLogger.log({
      category: 'data_access',
      action: 'data_exported',
      severity: 'warning',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: resourceType, id: resourceId },
      details: { format, recordCount },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA', 'GDPR'],
        retentionDays: 365 * 7,
      },
    }),

  created: (resourceType: string, resourceId: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'data_modification',
      action: 'data_created',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: resourceType, id: resourceId },
      details: {},
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365,
      },
    }),

  updated: (
    resourceType: string,
    resourceId: string,
    changes: Record<string, unknown>,
    options: LogOptions = {}
  ) =>
    auditLogger.log({
      category: 'data_modification',
      action: 'data_updated',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: resourceType, id: resourceId },
      details: { changes: Object.keys(changes) }, // Only log field names, not values
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365,
      },
    }),

  deleted: (resourceType: string, resourceId: string, reason: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'data_deletion',
      action: 'data_deleted',
      severity: 'warning',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: resourceType, id: resourceId },
      details: { reason },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'GDPR'],
        retentionDays: 365 * 7,
      },
    }),
};

/**
 * Log compliance-specific events
 */
export const complianceAudit = {
  consentGiven: (purpose: string, version: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'compliance',
      action: 'consent_given',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'consent', name: purpose },
      details: { purpose, policyVersion: version },
      outcome: 'success',
      compliance: {
        frameworks: ['GDPR'],
        retentionDays: 365 * 7,
      },
    }),

  consentWithdrawn: (purpose: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'compliance',
      action: 'consent_withdrawn',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'consent', name: purpose },
      details: { purpose },
      outcome: 'success',
      compliance: {
        frameworks: ['GDPR'],
        retentionDays: 365 * 7,
      },
    }),

  dsrSubmitted: (requestType: string, requestId: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'compliance',
      action: 'dsr_submitted',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'dsr', id: requestId },
      details: { requestType },
      outcome: 'success',
      compliance: {
        frameworks: ['GDPR'],
        retentionDays: 365 * 7,
      },
    }),

  dsrCompleted: (requestType: string, requestId: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'compliance',
      action: 'dsr_completed',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'dsr', id: requestId },
      details: { requestType },
      outcome: 'success',
      compliance: {
        frameworks: ['GDPR'],
        retentionDays: 365 * 7,
      },
    }),

  breachDetected: (breachId: string, severity: string, affectedRecords: number) =>
    auditLogger.log({
      category: 'compliance',
      action: 'breach_detected',
      severity: 'critical',
      actor: { userId: 'system' },
      resource: { type: 'breach', id: breachId },
      details: { severity, affectedRecords },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA', 'GDPR'],
        retentionDays: 365 * 7,
      },
    }),

  breachReported: (breachId: string, reportedTo: string[]) =>
    auditLogger.log({
      category: 'compliance',
      action: 'breach_reported',
      severity: 'critical',
      actor: { ...getCurrentUserContext() },
      resource: { type: 'breach', id: breachId },
      details: { reportedTo },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA', 'GDPR'],
        retentionDays: 365 * 7,
      },
    }),
};

/**
 * Log security events
 */
export const securityAudit = {
  suspiciousActivity: (activityType: string, details: Record<string, unknown>) =>
    auditLogger.log({
      category: 'security',
      action: 'suspicious_activity',
      severity: 'warning',
      actor: { ...getCurrentUserContext() },
      resource: { type: 'security_event' },
      details: { activityType, ...details },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA'],
        retentionDays: 365 * 7,
      },
    }),

  accessDenied: (resourceType: string, resourceId: string, reason: string) =>
    auditLogger.log({
      category: 'authorization',
      action: 'access_denied',
      severity: 'warning',
      actor: { ...getCurrentUserContext() },
      resource: { type: resourceType, id: resourceId },
      details: { reason },
      outcome: 'failure',
      errorMessage: reason,
      compliance: {
        frameworks: ['SOC2', 'HIPAA'],
        retentionDays: 365 * 7,
      },
    }),

  rateLimitExceeded: (endpoint: string, limit: number) =>
    auditLogger.log({
      category: 'security',
      action: 'rate_limit_exceeded',
      severity: 'warning',
      actor: { ...getCurrentUserContext() },
      resource: { type: 'api_endpoint', name: endpoint },
      details: { limit },
      outcome: 'failure',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365,
      },
    }),

  roleChanged: (
    targetUserId: string,
    oldRole: string,
    newRole: string,
    options: LogOptions = {}
  ) =>
    auditLogger.log({
      category: 'authorization',
      action: 'role_assigned',
      severity: 'warning',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'user', id: targetUserId },
      details: { oldRole, newRole },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2', 'HIPAA'],
        retentionDays: 365 * 7,
      },
    }),
};

/**
 * Log configuration changes
 */
export const configAudit = {
  settingChanged: (
    settingName: string,
    oldValue: unknown,
    newValue: unknown,
    options: LogOptions = {}
  ) =>
    auditLogger.log({
      category: 'configuration',
      action: 'setting_changed',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'setting', name: settingName },
      details: {
        oldValue: typeof oldValue === 'string' && oldValue.length > 50 ? '[REDACTED]' : oldValue,
        newValue: typeof newValue === 'string' && newValue.length > 50 ? '[REDACTED]' : newValue,
      },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365 * 7,
      },
    }),

  apiKeyCreated: (keyId: string, keyName: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'configuration',
      action: 'api_key_created',
      severity: 'warning',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'api_key', id: keyId, name: keyName },
      details: {},
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365 * 7,
      },
    }),

  apiKeyRevoked: (keyId: string, keyName: string, reason: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'configuration',
      action: 'api_key_revoked',
      severity: 'warning',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'api_key', id: keyId, name: keyName },
      details: { reason },
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365 * 7,
      },
    }),

  integrationAdded: (integrationId: string, integrationType: string, options: LogOptions = {}) =>
    auditLogger.log({
      category: 'configuration',
      action: 'integration_added',
      severity: 'info',
      actor: { ...getCurrentUserContext(), ...options },
      resource: { type: 'integration', id: integrationId, name: integrationType },
      details: {},
      outcome: 'success',
      compliance: {
        frameworks: ['SOC2'],
        retentionDays: 365,
      },
    }),
};

export default auditLogger;
