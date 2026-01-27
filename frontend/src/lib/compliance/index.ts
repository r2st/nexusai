/**
 * Compliance Module
 *
 * Centralized exports for SOC2, HIPAA, and GDPR compliance features.
 */

// Types
export * from './types';

// Audit Logging
export {
  auditLogger,
  authAudit,
  dataAudit,
  complianceAudit,
  securityAudit,
  configAudit,
  type AuditEvent,
  type AuditCategory,
  type AuditAction,
  type AuditSeverity,
} from './audit';

// Encryption
export {
  encrypt,
  decrypt,
  encryptWithPassword,
  decryptWithPassword,
  hash,
  hashSHA512,
  hmac,
  verifyHmac,
  generateKey,
  deriveKey,
  exportKey,
  importKey,
  secureRandom,
  secureRandomString,
  secureUUID,
  maskData,
  redactSensitiveFields,
  autoRedactSensitive,
  isSensitiveField,
  secureStore,
  secureRetrieve,
  secureRemove,
  secureClearAll,
  needsKeyRotation,
  generateKeyRotationSchedule,
  SENSITIVE_FIELD_PATTERNS,
  type EncryptedData,
  type KeyRotationInfo,
} from './encryption';

// GDPR Consent Management
export {
  consentManager,
  useConsent,
  useAnalyticsConsent,
  useMarketingConsent,
  getStoredConsent,
  clearStoredConsent,
  withConsent,
  loadAnalyticsIfConsented,
  canProcessData,
  getConsentSummary,
  CONSENT_PURPOSES,
  CURRENT_PRIVACY_VERSION,
} from './consent';

// GDPR Data Subject Rights
export {
  dsrService,
  useDataSubjectRights,
  useDataDeletion,
  useDataExport,
  getDSRStatusLabel,
  getDSRStatusColor,
  getDaysRemaining,
  isDSROverdue,
  DSR_CONFIG,
} from './data-subject-rights';

// Data Retention
export {
  retentionService,
  useRetentionPolicies,
  useRetentionCleanup,
  formatRetentionPeriod,
  getDaysUntilExpiration,
  isUnderLegalHold,
  RETENTION_POLICIES,
} from './retention';

// HIPAA
export {
  detectPHI,
  redactPHI,
  deidentify,
  requiresHIPAAProtection,
  determineAccessLevel,
  applyMinimumNecessary,
  logPHIAccess,
  getHIPAAControlsBySafeguard,
  getRequiredHIPAAControls,
  assessBreachRisk,
  HIPAA_PHI_IDENTIFIERS,
  HIPAA_CONTROLS,
  type PHIDetectionResult,
  type HIPAAAccessLevel,
  type HIPAAAccessContext,
  type BreachRiskAssessment,
} from './hipaa';
