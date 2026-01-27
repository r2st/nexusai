/**
 * Compliance Types and Interfaces
 *
 * Defines types for SOC2, HIPAA, and GDPR compliance features.
 */

// =============================================================================
// COMPLIANCE FRAMEWORKS
// =============================================================================

export type ComplianceFramework = 'SOC2' | 'HIPAA' | 'GDPR';

export type ComplianceStatus = 'compliant' | 'non_compliant' | 'partial' | 'not_applicable';

export interface ComplianceControl {
  id: string;
  framework: ComplianceFramework;
  category: string;
  name: string;
  description: string;
  status: ComplianceStatus;
  evidence?: string[];
  lastAssessed?: string;
  nextAssessment?: string;
}

// =============================================================================
// SOC2 - Security, Availability, Processing Integrity, Confidentiality, Privacy
// =============================================================================

export type SOC2TrustCategory =
  | 'security'
  | 'availability'
  | 'processing_integrity'
  | 'confidentiality'
  | 'privacy';

export interface SOC2Control extends ComplianceControl {
  framework: 'SOC2';
  trustCategory: SOC2TrustCategory;
  controlNumber: string; // e.g., CC1.1, CC2.1
}

export const SOC2_CATEGORIES: Record<SOC2TrustCategory, string> = {
  security: 'Security (Common Criteria)',
  availability: 'Availability',
  processing_integrity: 'Processing Integrity',
  confidentiality: 'Confidentiality',
  privacy: 'Privacy',
};

// =============================================================================
// HIPAA - Health Insurance Portability and Accountability Act
// =============================================================================

export type HIPAARuleType =
  | 'privacy_rule'
  | 'security_rule'
  | 'breach_notification'
  | 'enforcement_rule';

export type HIPAASafeguardType =
  | 'administrative'
  | 'physical'
  | 'technical';

export interface HIPAAControl extends ComplianceControl {
  framework: 'HIPAA';
  ruleType: HIPAARuleType;
  safeguardType?: HIPAASafeguardType;
  cfr: string; // Code of Federal Regulations reference
  required: boolean;
  addressable: boolean;
}

export interface PHIDataElement {
  id: string;
  name: string;
  description: string;
  category: 'direct_identifier' | 'quasi_identifier' | 'sensitive';
  encrypted: boolean;
  minimized: boolean;
}

export const HIPAA_IDENTIFIERS: string[] = [
  'name',
  'address',
  'dates',
  'phone_numbers',
  'fax_numbers',
  'email_addresses',
  'ssn',
  'mrn', // Medical Record Number
  'health_plan_id',
  'account_numbers',
  'certificate_numbers',
  'vehicle_identifiers',
  'device_identifiers',
  'urls',
  'ip_addresses',
  'biometric_identifiers',
  'photos',
  'other_unique_identifiers',
];

// =============================================================================
// GDPR - General Data Protection Regulation
// =============================================================================

export type GDPRLawfulBasis =
  | 'consent'
  | 'contract'
  | 'legal_obligation'
  | 'vital_interests'
  | 'public_task'
  | 'legitimate_interests';

export type GDPRDataSubjectRight =
  | 'access'
  | 'rectification'
  | 'erasure'
  | 'restriction'
  | 'portability'
  | 'objection'
  | 'automated_decision';

export type GDPRArticle =
  | 'article_5'   // Principles
  | 'article_6'   // Lawful basis
  | 'article_7'   // Consent
  | 'article_12'  // Transparent information
  | 'article_13'  // Information at collection
  | 'article_14'  // Information not obtained from data subject
  | 'article_15'  // Right of access
  | 'article_16'  // Right to rectification
  | 'article_17'  // Right to erasure
  | 'article_18'  // Right to restriction
  | 'article_20'  // Right to data portability
  | 'article_21'  // Right to object
  | 'article_22'  // Automated decision-making
  | 'article_25'  // Data protection by design
  | 'article_30'  // Records of processing
  | 'article_32'  // Security of processing
  | 'article_33'  // Breach notification
  | 'article_35'  // DPIA
  | 'article_44'; // International transfers

export interface GDPRControl extends ComplianceControl {
  framework: 'GDPR';
  article: GDPRArticle;
  principle?: string;
}

// =============================================================================
// CONSENT MANAGEMENT
// =============================================================================

export type ConsentPurpose =
  | 'essential'
  | 'analytics'
  | 'marketing'
  | 'personalization'
  | 'third_party'
  | 'ai_training'
  | 'data_sharing';

export interface ConsentRecord {
  id: string;
  userId: string;
  purpose: ConsentPurpose;
  granted: boolean;
  timestamp: string;
  ipAddress?: string;
  userAgent?: string;
  version: string; // Privacy policy version
  expiresAt?: string;
  withdrawnAt?: string;
}

export interface ConsentPreferences {
  essential: boolean; // Always true, required for operation
  analytics: boolean;
  marketing: boolean;
  personalization: boolean;
  thirdParty: boolean;
  aiTraining: boolean;
  dataSharing: boolean;
  updatedAt: string;
}

// =============================================================================
// DATA SUBJECT REQUESTS (DSR)
// =============================================================================

export type DSRType =
  | 'access'
  | 'rectification'
  | 'erasure'
  | 'restriction'
  | 'portability'
  | 'objection';

export type DSRStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'rejected'
  | 'expired';

export interface DataSubjectRequest {
  id: string;
  userId: string;
  email: string;
  type: DSRType;
  status: DSRStatus;
  reason?: string;
  submittedAt: string;
  acknowledgedAt?: string;
  completedAt?: string;
  dueDate: string; // GDPR requires 30 days
  response?: string;
  dataExport?: string; // URL to exported data
  verificationMethod: 'email' | 'id_document' | 'account_login';
  verified: boolean;
}

// =============================================================================
// DATA RETENTION
// =============================================================================

export interface RetentionPolicy {
  id: string;
  dataCategory: string;
  description: string;
  retentionPeriod: number; // in days
  legalBasis: string;
  framework: ComplianceFramework[];
  autoDelete: boolean;
  reviewRequired: boolean;
}

export const DEFAULT_RETENTION_POLICIES: RetentionPolicy[] = [
  {
    id: 'user_account',
    dataCategory: 'User Account Data',
    description: 'Basic user profile and authentication data',
    retentionPeriod: 365 * 3, // 3 years after account closure
    legalBasis: 'Contract fulfillment and legal obligation',
    framework: ['SOC2', 'GDPR', 'HIPAA'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'audit_logs',
    dataCategory: 'Audit Logs',
    description: 'Security and compliance audit trail',
    retentionPeriod: 365 * 7, // 7 years for SOC2/HIPAA
    legalBasis: 'Legal obligation and legitimate interest',
    framework: ['SOC2', 'HIPAA'],
    autoDelete: false,
    reviewRequired: true,
  },
  {
    id: 'chat_history',
    dataCategory: 'Chat Conversations',
    description: 'User chat messages and AI responses',
    retentionPeriod: 365, // 1 year
    legalBasis: 'Contract and consent',
    framework: ['GDPR', 'SOC2'],
    autoDelete: true,
    reviewRequired: false,
  },
  {
    id: 'analytics_data',
    dataCategory: 'Analytics Data',
    description: 'Usage analytics and metrics',
    retentionPeriod: 365 * 2, // 2 years
    legalBasis: 'Legitimate interest',
    framework: ['GDPR'],
    autoDelete: true,
    reviewRequired: false,
  },
  {
    id: 'session_data',
    dataCategory: 'Session Data',
    description: 'Login sessions and activity logs',
    retentionPeriod: 90, // 90 days
    legalBasis: 'Security and legitimate interest',
    framework: ['SOC2', 'GDPR'],
    autoDelete: true,
    reviewRequired: false,
  },
  {
    id: 'phi_data',
    dataCategory: 'Protected Health Information',
    description: 'Any health-related data processed',
    retentionPeriod: 365 * 6, // 6 years per HIPAA
    legalBasis: 'HIPAA requirement',
    framework: ['HIPAA'],
    autoDelete: false,
    reviewRequired: true,
  },
];

// =============================================================================
// BREACH NOTIFICATION
// =============================================================================

export type BreachSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface DataBreach {
  id: string;
  detectedAt: string;
  occurredAt?: string;
  reportedAt?: string;
  severity: BreachSeverity;
  description: string;
  affectedRecords: number;
  dataTypes: string[];
  containmentStatus: 'detected' | 'contained' | 'eradicated' | 'recovered';
  notificationStatus: {
    authorities: boolean;
    dataSubjects: boolean;
    notifiedAt?: string;
  };
  rootCause?: string;
  remediation?: string;
  frameworks: ComplianceFramework[];
}

// =============================================================================
// ENCRYPTION
// =============================================================================

export type EncryptionState = 'at_rest' | 'in_transit' | 'in_use';

export interface EncryptionConfig {
  algorithm: string;
  keyLength: number;
  state: EncryptionState;
  keyRotationDays: number;
  lastRotated?: string;
}

export const ENCRYPTION_STANDARDS: Record<string, EncryptionConfig> = {
  aes256: {
    algorithm: 'AES-256-GCM',
    keyLength: 256,
    state: 'at_rest',
    keyRotationDays: 90,
  },
  tls13: {
    algorithm: 'TLS 1.3',
    keyLength: 256,
    state: 'in_transit',
    keyRotationDays: 365,
  },
};

// =============================================================================
// ACCESS CONTROL
// =============================================================================

export interface AccessControlPolicy {
  id: string;
  resource: string;
  actions: string[];
  conditions?: Record<string, unknown>;
  effect: 'allow' | 'deny';
  priority: number;
}

export interface AccessLog {
  id: string;
  userId: string;
  resource: string;
  action: string;
  timestamp: string;
  ipAddress: string;
  userAgent: string;
  result: 'allowed' | 'denied';
  reason?: string;
}

// =============================================================================
// COMPLIANCE REPORT
// =============================================================================

export interface ComplianceReport {
  id: string;
  framework: ComplianceFramework;
  generatedAt: string;
  period: {
    start: string;
    end: string;
  };
  overallStatus: ComplianceStatus;
  controlsSummary: {
    total: number;
    compliant: number;
    nonCompliant: number;
    partial: number;
    notApplicable: number;
  };
  findings: ComplianceFinding[];
  recommendations: string[];
}

export interface ComplianceFinding {
  id: string;
  controlId: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  remediation: string;
  dueDate?: string;
  status: 'open' | 'in_progress' | 'resolved' | 'accepted';
}
