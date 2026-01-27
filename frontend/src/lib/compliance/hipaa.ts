/**
 * HIPAA Compliance Utilities
 *
 * Implements HIPAA Security Rule and Privacy Rule requirements
 * for handling Protected Health Information (PHI).
 */

import { dataAudit } from './audit';
import { maskData, autoRedactSensitive, SENSITIVE_FIELD_PATTERNS } from './encryption';
import type { PHIDataElement, HIPAAControl, HIPAASafeguardType } from './types';

// =============================================================================
// PHI IDENTIFIERS (18 HIPAA Identifiers)
// =============================================================================

export const HIPAA_PHI_IDENTIFIERS: PHIDataElement[] = [
  { id: 'name', name: 'Names', description: 'Full name or any part of name', category: 'direct_identifier', encrypted: true, minimized: false },
  { id: 'geographic', name: 'Geographic Data', description: 'Address, city, ZIP (smaller than state)', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'dates', name: 'Dates', description: 'Birth date, admission date, discharge date, death date, ages over 89', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'phone', name: 'Phone Numbers', description: 'All telephone numbers', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'fax', name: 'Fax Numbers', description: 'All fax numbers', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'email', name: 'Email Addresses', description: 'Electronic mail addresses', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'ssn', name: 'Social Security Numbers', description: 'SSN', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'mrn', name: 'Medical Record Numbers', description: 'MRN and health record identifiers', category: 'direct_identifier', encrypted: true, minimized: false },
  { id: 'health_plan_id', name: 'Health Plan IDs', description: 'Health plan beneficiary numbers', category: 'direct_identifier', encrypted: true, minimized: false },
  { id: 'account_numbers', name: 'Account Numbers', description: 'Financial account numbers', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'license_numbers', name: 'License Numbers', description: 'Certificate/license numbers', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'vehicle_ids', name: 'Vehicle Identifiers', description: 'Vehicle IDs and serial numbers, license plates', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'device_ids', name: 'Device Identifiers', description: 'Medical device identifiers and serial numbers', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'urls', name: 'Web URLs', description: 'Web Universal Resource Locators', category: 'quasi_identifier', encrypted: false, minimized: true },
  { id: 'ip_addresses', name: 'IP Addresses', description: 'Internet Protocol addresses', category: 'quasi_identifier', encrypted: false, minimized: true },
  { id: 'biometric', name: 'Biometric Identifiers', description: 'Fingerprints, voiceprints, retinal scans', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'photos', name: 'Photographs', description: 'Full-face photographs and comparable images', category: 'direct_identifier', encrypted: true, minimized: true },
  { id: 'other_unique', name: 'Other Unique IDs', description: 'Any other unique identifying number or code', category: 'direct_identifier', encrypted: true, minimized: true },
];

// PHI detection patterns
const PHI_PATTERNS: Record<string, RegExp> = {
  ssn: /\b\d{3}-?\d{2}-?\d{4}\b/g,
  mrn: /\b(MRN|mrn|Medical Record)[:\s#]*\d{4,}\b/gi,
  phone: /\b(\+1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b/g,
  email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
  date_of_birth: /\b(DOB|dob|Date of Birth|Birth Date)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/gi,
  health_plan: /\b(Member ID|Plan ID|Insurance ID)[:\s#]*[A-Z0-9]{6,}\b/gi,
};

// =============================================================================
// PHI DETECTION & PROTECTION
// =============================================================================

export interface PHIDetectionResult {
  containsPHI: boolean;
  identifiers: {
    type: string;
    value: string;
    location: { start: number; end: number };
  }[];
  risk: 'low' | 'medium' | 'high';
}

/**
 * Detect PHI in text content
 */
export function detectPHI(text: string): PHIDetectionResult {
  const identifiers: PHIDetectionResult['identifiers'] = [];

  for (const [type, pattern] of Object.entries(PHI_PATTERNS)) {
    let match;
    const regex = new RegExp(pattern.source, pattern.flags);

    while ((match = regex.exec(text)) !== null) {
      identifiers.push({
        type,
        value: match[0],
        location: { start: match.index, end: match.index + match[0].length },
      });
    }
  }

  const containsPHI = identifiers.length > 0;
  const risk = identifiers.length === 0 ? 'low' :
    identifiers.length <= 2 ? 'medium' : 'high';

  return { containsPHI, identifiers, risk };
}

/**
 * Redact PHI from text
 */
export function redactPHI(text: string): string {
  let redacted = text;

  for (const pattern of Object.values(PHI_PATTERNS)) {
    redacted = redacted.replace(pattern, '[REDACTED]');
  }

  return redacted;
}

/**
 * De-identify data according to HIPAA Safe Harbor method
 */
export function deidentify<T extends Record<string, unknown>>(data: T): T {
  const result = { ...data };

  // Remove all 18 HIPAA identifiers
  const fieldsToRedact = [
    ...SENSITIVE_FIELD_PATTERNS.phi,
    'name', 'first_name', 'last_name', 'address', 'city', 'zip',
    'postal_code', 'phone', 'fax', 'email', 'ssn', 'mrn',
    'dob', 'birth_date', 'date_of_birth', 'license', 'vehicle',
    'device_id', 'biometric', 'photo', 'image',
  ];

  for (const key of Object.keys(result)) {
    const lowerKey = key.toLowerCase();
    if (fieldsToRedact.some(field => lowerKey.includes(field))) {
      result[key as keyof T] = '[DE-IDENTIFIED]' as T[keyof T];
    }
  }

  // Handle dates - generalize to year only for ages under 90
  if ('date_of_birth' in result || 'dob' in result) {
    const dobKey = 'date_of_birth' in result ? 'date_of_birth' : 'dob';
    const dob = result[dobKey] as string;
    if (dob) {
      const birthYear = new Date(dob).getFullYear();
      const age = new Date().getFullYear() - birthYear;
      if (age >= 90) {
        result[dobKey as keyof T] = '90+' as T[keyof T];
      } else {
        result[dobKey as keyof T] = String(birthYear) as T[keyof T];
      }
    }
  }

  // Generalize geographic data to state level
  if ('zip' in result || 'postal_code' in result) {
    const zipKey = 'zip' in result ? 'zip' : 'postal_code';
    result[zipKey as keyof T] = '[STATE-ONLY]' as T[keyof T];
  }

  return result;
}

/**
 * Check if data contains PHI requiring special handling
 */
export function requiresHIPAAProtection(data: Record<string, unknown>): boolean {
  const stringified = JSON.stringify(data).toLowerCase();

  // Check for PHI field names
  const phiFields = SENSITIVE_FIELD_PATTERNS.phi;
  for (const field of phiFields) {
    if (stringified.includes(field)) {
      return true;
    }
  }

  // Check for PHI patterns in values
  const detection = detectPHI(stringified);
  return detection.containsPHI;
}

// =============================================================================
// HIPAA ACCESS CONTROLS
// =============================================================================

export type HIPAAAccessLevel = 'none' | 'minimum_necessary' | 'full';

export interface HIPAAAccessContext {
  userId: string;
  role: string;
  purpose: string;
  patientRelationship?: 'self' | 'provider' | 'authorized_representative' | 'none';
}

/**
 * Determine access level based on HIPAA minimum necessary standard
 */
export function determineAccessLevel(
  context: HIPAAAccessContext,
  dataCategory: string
): HIPAAAccessLevel {
  // Self-access is always full
  if (context.patientRelationship === 'self') {
    return 'full';
  }

  // Healthcare providers with treatment purpose
  if (
    context.patientRelationship === 'provider' &&
    context.purpose === 'treatment'
  ) {
    return 'full';
  }

  // Authorized representatives
  if (context.patientRelationship === 'authorized_representative') {
    return 'full';
  }

  // Administrative users - minimum necessary
  if (context.role === 'admin' || context.role === 'staff') {
    return 'minimum_necessary';
  }

  return 'none';
}

/**
 * Apply minimum necessary principle to data
 */
export function applyMinimumNecessary<T extends Record<string, unknown>>(
  data: T,
  allowedFields: string[]
): Partial<T> {
  const result: Partial<T> = {};

  for (const field of allowedFields) {
    if (field in data) {
      result[field as keyof T] = data[field as keyof T];
    }
  }

  return result;
}

// =============================================================================
// HIPAA AUDIT REQUIREMENTS
// =============================================================================

/**
 * Log PHI access for HIPAA audit trail
 */
export async function logPHIAccess(
  resourceId: string,
  accessType: 'view' | 'create' | 'update' | 'delete' | 'export',
  purpose: string,
  userId?: string
): Promise<void> {
  await dataAudit.accessed('phi', resourceId, true, false, { userId });

  // Additional HIPAA-specific logging
  console.log('[HIPAA AUDIT]', {
    timestamp: new Date().toISOString(),
    resourceId,
    accessType,
    purpose,
    userId,
  });
}

/**
 * Generate HIPAA access report
 */
export interface HIPAAAccessReport {
  userId: string;
  patientId: string;
  accessHistory: {
    timestamp: string;
    action: string;
    dataAccessed: string[];
    purpose: string;
  }[];
}

// =============================================================================
// HIPAA SECURITY CONTROLS
// =============================================================================

export const HIPAA_CONTROLS: HIPAAControl[] = [
  // Administrative Safeguards (164.308)
  {
    id: 'hipaa-admin-1',
    framework: 'HIPAA',
    category: 'Administrative Safeguards',
    name: 'Security Management Process',
    description: 'Implement policies and procedures to prevent, detect, contain, and correct security violations',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'administrative',
    cfr: '164.308(a)(1)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-admin-2',
    framework: 'HIPAA',
    category: 'Administrative Safeguards',
    name: 'Workforce Security',
    description: 'Implement policies and procedures to ensure appropriate access for workforce members',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'administrative',
    cfr: '164.308(a)(3)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-admin-3',
    framework: 'HIPAA',
    category: 'Administrative Safeguards',
    name: 'Information Access Management',
    description: 'Implement policies and procedures for authorizing access to PHI',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'administrative',
    cfr: '164.308(a)(4)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-admin-4',
    framework: 'HIPAA',
    category: 'Administrative Safeguards',
    name: 'Security Awareness Training',
    description: 'Implement security awareness and training program for workforce',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'administrative',
    cfr: '164.308(a)(5)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-admin-5',
    framework: 'HIPAA',
    category: 'Administrative Safeguards',
    name: 'Contingency Plan',
    description: 'Establish policies and procedures for responding to emergencies',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'administrative',
    cfr: '164.308(a)(7)',
    required: true,
    addressable: false,
  },

  // Physical Safeguards (164.310)
  {
    id: 'hipaa-phys-1',
    framework: 'HIPAA',
    category: 'Physical Safeguards',
    name: 'Facility Access Controls',
    description: 'Implement policies to limit physical access to electronic information systems',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'physical',
    cfr: '164.310(a)(1)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-phys-2',
    framework: 'HIPAA',
    category: 'Physical Safeguards',
    name: 'Workstation Security',
    description: 'Implement physical safeguards for workstations accessing PHI',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'physical',
    cfr: '164.310(c)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-phys-3',
    framework: 'HIPAA',
    category: 'Physical Safeguards',
    name: 'Device and Media Controls',
    description: 'Implement policies for receipt and removal of hardware and media',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'physical',
    cfr: '164.310(d)(1)',
    required: true,
    addressable: false,
  },

  // Technical Safeguards (164.312)
  {
    id: 'hipaa-tech-1',
    framework: 'HIPAA',
    category: 'Technical Safeguards',
    name: 'Access Control',
    description: 'Implement technical policies to allow only authorized access to PHI',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'technical',
    cfr: '164.312(a)(1)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-tech-2',
    framework: 'HIPAA',
    category: 'Technical Safeguards',
    name: 'Audit Controls',
    description: 'Implement mechanisms to record and examine access to PHI',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'technical',
    cfr: '164.312(b)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-tech-3',
    framework: 'HIPAA',
    category: 'Technical Safeguards',
    name: 'Integrity Controls',
    description: 'Implement policies to protect PHI from improper alteration or destruction',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'technical',
    cfr: '164.312(c)(1)',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-tech-4',
    framework: 'HIPAA',
    category: 'Technical Safeguards',
    name: 'Transmission Security',
    description: 'Implement measures to guard against unauthorized access to PHI during transmission',
    status: 'compliant',
    ruleType: 'security_rule',
    safeguardType: 'technical',
    cfr: '164.312(e)(1)',
    required: true,
    addressable: false,
  },

  // Breach Notification (164.400-414)
  {
    id: 'hipaa-breach-1',
    framework: 'HIPAA',
    category: 'Breach Notification',
    name: 'Breach Notification to Individuals',
    description: 'Notify affected individuals following discovery of breach of unsecured PHI',
    status: 'compliant',
    ruleType: 'breach_notification',
    cfr: '164.404',
    required: true,
    addressable: false,
  },
  {
    id: 'hipaa-breach-2',
    framework: 'HIPAA',
    category: 'Breach Notification',
    name: 'Notification to HHS',
    description: 'Notify Secretary of HHS following discovery of breach of unsecured PHI',
    status: 'compliant',
    ruleType: 'breach_notification',
    cfr: '164.408',
    required: true,
    addressable: false,
  },
];

/**
 * Get HIPAA controls by safeguard type
 */
export function getHIPAAControlsBySafeguard(
  safeguardType: HIPAASafeguardType
): HIPAAControl[] {
  return HIPAA_CONTROLS.filter(c => c.safeguardType === safeguardType);
}

/**
 * Get all required HIPAA controls
 */
export function getRequiredHIPAAControls(): HIPAAControl[] {
  return HIPAA_CONTROLS.filter(c => c.required);
}

// =============================================================================
// HIPAA BREACH ASSESSMENT
// =============================================================================

export interface BreachRiskAssessment {
  isBreachReportable: boolean;
  riskLevel: 'low' | 'medium' | 'high';
  factors: {
    factor: string;
    assessment: string;
    mitigated: boolean;
  }[];
  recommendedActions: string[];
}

/**
 * Assess breach risk according to HIPAA guidance
 */
export function assessBreachRisk(incident: {
  phiType: string[];
  numRecords: number;
  wasEncrypted: boolean;
  wasAccessedByUnauthorized: boolean;
  wasMitigated: boolean;
}): BreachRiskAssessment {
  const factors = [];
  let riskScore = 0;

  // Factor 1: Nature and extent of PHI
  const sensitiveTypes = ['ssn', 'mrn', 'diagnosis', 'treatment'];
  const hasSensitive = incident.phiType.some(t => sensitiveTypes.includes(t));
  factors.push({
    factor: 'Nature and extent of PHI involved',
    assessment: hasSensitive ? 'Contains sensitive identifiers' : 'Limited PHI types',
    mitigated: !hasSensitive,
  });
  if (hasSensitive) riskScore += 2;

  // Factor 2: Unauthorized person
  factors.push({
    factor: 'Unauthorized person who used/accessed PHI',
    assessment: incident.wasAccessedByUnauthorized
      ? 'PHI was accessed by unauthorized party'
      : 'No evidence of unauthorized access',
    mitigated: !incident.wasAccessedByUnauthorized,
  });
  if (incident.wasAccessedByUnauthorized) riskScore += 3;

  // Factor 3: PHI actually acquired or viewed
  factors.push({
    factor: 'Whether PHI was actually acquired or viewed',
    assessment: incident.wasAccessedByUnauthorized
      ? 'Evidence suggests PHI was viewed/acquired'
      : 'No evidence PHI was viewed',
    mitigated: !incident.wasAccessedByUnauthorized,
  });

  // Factor 4: Extent of risk mitigation
  factors.push({
    factor: 'Extent to which risk has been mitigated',
    assessment: incident.wasMitigated
      ? 'Risk has been mitigated'
      : 'Risk mitigation incomplete',
    mitigated: incident.wasMitigated,
  });
  if (incident.wasMitigated) riskScore -= 1;

  // Encryption factor
  if (incident.wasEncrypted) {
    factors.push({
      factor: 'Data encryption status',
      assessment: 'PHI was encrypted per HIPAA standards',
      mitigated: true,
    });
    riskScore = 0; // Encrypted data generally not considered breach
  }

  const riskLevel = riskScore <= 1 ? 'low' : riskScore <= 3 ? 'medium' : 'high';
  const isBreachReportable = riskLevel !== 'low' && !incident.wasEncrypted;

  const recommendedActions = [];
  if (isBreachReportable) {
    recommendedActions.push('Notify affected individuals within 60 days');
    if (incident.numRecords >= 500) {
      recommendedActions.push('Notify HHS immediately');
      recommendedActions.push('Notify prominent media outlets in affected states');
    } else {
      recommendedActions.push('Log breach for annual HHS notification');
    }
  }
  recommendedActions.push('Document risk assessment');
  recommendedActions.push('Implement additional safeguards');

  return {
    isBreachReportable,
    riskLevel,
    factors,
    recommendedActions,
  };
}
