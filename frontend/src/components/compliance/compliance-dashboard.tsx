'use client';

import { useState, useMemo } from 'react';
import {
  Shield,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Clock,
  ChevronDown,
  ChevronRight,
  Download,
  RefreshCw,
  Building2,
  Lock,
  Eye,
  Database,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  useRetentionPolicies,
  formatRetentionPeriod,
  HIPAA_CONTROLS,
  type ComplianceFramework,
  type ComplianceStatus,
  type ComplianceControl,
  type SOC2TrustCategory,
  SOC2_CATEGORIES,
} from '@/lib/compliance';

// =============================================================================
// SOC2 CONTROLS (Trust Service Criteria)
// =============================================================================

const SOC2_CONTROLS: ComplianceControl[] = [
  // Security (Common Criteria)
  { id: 'cc1.1', framework: 'SOC2', category: 'Security', name: 'Control Environment', description: 'The entity demonstrates commitment to integrity and ethical values', status: 'compliant' },
  { id: 'cc1.2', framework: 'SOC2', category: 'Security', name: 'Board Independence', description: 'The board of directors demonstrates independence from management', status: 'compliant' },
  { id: 'cc2.1', framework: 'SOC2', category: 'Security', name: 'Information Communication', description: 'Internal communication of objectives and responsibilities', status: 'compliant' },
  { id: 'cc3.1', framework: 'SOC2', category: 'Security', name: 'Risk Assessment', description: 'Entity specifies objectives and identifies risks', status: 'compliant' },
  { id: 'cc4.1', framework: 'SOC2', category: 'Security', name: 'Monitoring Activities', description: 'Ongoing and separate evaluations of controls', status: 'compliant' },
  { id: 'cc5.1', framework: 'SOC2', category: 'Security', name: 'Control Activities', description: 'Entity selects and develops control activities', status: 'compliant' },
  { id: 'cc6.1', framework: 'SOC2', category: 'Security', name: 'Logical Access', description: 'Logical access security measures implemented', status: 'compliant' },
  { id: 'cc6.2', framework: 'SOC2', category: 'Security', name: 'System Access', description: 'Prior to issuing system credentials, registration and authorization', status: 'compliant' },
  { id: 'cc6.3', framework: 'SOC2', category: 'Security', name: 'Access Removal', description: 'Process for removing credential access when no longer needed', status: 'compliant' },
  { id: 'cc6.6', framework: 'SOC2', category: 'Security', name: 'Boundary Protection', description: 'Security measures at system boundaries', status: 'compliant' },
  { id: 'cc6.7', framework: 'SOC2', category: 'Security', name: 'Data Transmission', description: 'Data transmission restricted to authorized users', status: 'compliant' },
  { id: 'cc7.1', framework: 'SOC2', category: 'Security', name: 'Vulnerability Management', description: 'Detection and monitoring of security vulnerabilities', status: 'compliant' },
  { id: 'cc7.2', framework: 'SOC2', category: 'Security', name: 'Incident Monitoring', description: 'Monitoring for security incidents and anomalies', status: 'compliant' },
  { id: 'cc8.1', framework: 'SOC2', category: 'Security', name: 'Change Management', description: 'Changes to infrastructure are authorized and tested', status: 'compliant' },
  { id: 'cc9.1', framework: 'SOC2', category: 'Security', name: 'Risk Mitigation', description: 'Risk mitigation activities are performed', status: 'compliant' },

  // Availability
  { id: 'a1.1', framework: 'SOC2', category: 'Availability', name: 'Capacity Management', description: 'Current capacity and planned availability requirements', status: 'compliant' },
  { id: 'a1.2', framework: 'SOC2', category: 'Availability', name: 'Environmental Protection', description: 'Environmental protections and backup infrastructure', status: 'compliant' },
  { id: 'a1.3', framework: 'SOC2', category: 'Availability', name: 'Recovery Testing', description: 'Recovery plan procedures are tested periodically', status: 'compliant' },

  // Confidentiality
  { id: 'c1.1', framework: 'SOC2', category: 'Confidentiality', name: 'Data Classification', description: 'Confidential information is identified and classified', status: 'compliant' },
  { id: 'c1.2', framework: 'SOC2', category: 'Confidentiality', name: 'Data Disposal', description: 'Confidential information is disposed of securely', status: 'compliant' },

  // Privacy
  { id: 'p1.1', framework: 'SOC2', category: 'Privacy', name: 'Privacy Notice', description: 'Privacy notice is provided to data subjects', status: 'compliant' },
  { id: 'p2.1', framework: 'SOC2', category: 'Privacy', name: 'Consent', description: 'Consent is obtained for collection and use of personal data', status: 'compliant' },
  { id: 'p3.1', framework: 'SOC2', category: 'Privacy', name: 'Data Collection', description: 'Personal information is collected consistent with objectives', status: 'compliant' },
  { id: 'p4.1', framework: 'SOC2', category: 'Privacy', name: 'Data Use', description: 'Personal information is used only for stated purposes', status: 'compliant' },
  { id: 'p5.1', framework: 'SOC2', category: 'Privacy', name: 'Data Retention', description: 'Personal information is retained only as needed', status: 'compliant' },
  { id: 'p6.1', framework: 'SOC2', category: 'Privacy', name: 'Data Access', description: 'Data subjects can access their personal information', status: 'compliant' },
  { id: 'p7.1', framework: 'SOC2', category: 'Privacy', name: 'Data Disclosure', description: 'Personal information is disclosed only to authorized parties', status: 'compliant' },
  { id: 'p8.1', framework: 'SOC2', category: 'Privacy', name: 'Data Quality', description: 'Personal information is accurate and complete', status: 'compliant' },
];

// GDPR Controls (Selected Articles)
const GDPR_CONTROLS: ComplianceControl[] = [
  { id: 'gdpr-5', framework: 'GDPR', category: 'Principles', name: 'Data Processing Principles', description: 'Lawfulness, fairness, transparency, purpose limitation, data minimization', status: 'compliant' },
  { id: 'gdpr-6', framework: 'GDPR', category: 'Lawful Basis', name: 'Lawful Basis for Processing', description: 'Valid legal basis for all data processing activities', status: 'compliant' },
  { id: 'gdpr-7', framework: 'GDPR', category: 'Consent', name: 'Consent Management', description: 'Clear, affirmative consent for data processing', status: 'compliant' },
  { id: 'gdpr-12', framework: 'GDPR', category: 'Transparency', name: 'Transparent Information', description: 'Clear, accessible privacy information', status: 'compliant' },
  { id: 'gdpr-15', framework: 'GDPR', category: 'Data Subject Rights', name: 'Right of Access', description: 'Data subjects can access their personal data', status: 'compliant' },
  { id: 'gdpr-16', framework: 'GDPR', category: 'Data Subject Rights', name: 'Right to Rectification', description: 'Data subjects can correct inaccurate data', status: 'compliant' },
  { id: 'gdpr-17', framework: 'GDPR', category: 'Data Subject Rights', name: 'Right to Erasure', description: 'Data subjects can request data deletion', status: 'compliant' },
  { id: 'gdpr-18', framework: 'GDPR', category: 'Data Subject Rights', name: 'Right to Restriction', description: 'Data subjects can restrict processing', status: 'compliant' },
  { id: 'gdpr-20', framework: 'GDPR', category: 'Data Subject Rights', name: 'Right to Portability', description: 'Data subjects can export their data', status: 'compliant' },
  { id: 'gdpr-21', framework: 'GDPR', category: 'Data Subject Rights', name: 'Right to Object', description: 'Data subjects can object to processing', status: 'compliant' },
  { id: 'gdpr-25', framework: 'GDPR', category: 'Security', name: 'Privacy by Design', description: 'Data protection built into systems', status: 'compliant' },
  { id: 'gdpr-30', framework: 'GDPR', category: 'Documentation', name: 'Records of Processing', description: 'Maintained records of processing activities', status: 'compliant' },
  { id: 'gdpr-32', framework: 'GDPR', category: 'Security', name: 'Security of Processing', description: 'Appropriate technical and organizational measures', status: 'compliant' },
  { id: 'gdpr-33', framework: 'GDPR', category: 'Breach', name: 'Breach Notification', description: '72-hour breach notification to authorities', status: 'compliant' },
  { id: 'gdpr-35', framework: 'GDPR', category: 'Risk Assessment', name: 'Data Protection Impact Assessment', description: 'DPIA for high-risk processing', status: 'compliant' },
];

// =============================================================================
// COMPLIANCE DASHBOARD
// =============================================================================

export function ComplianceDashboard() {
  const [selectedFramework, setSelectedFramework] = useState<ComplianceFramework | 'all'>('all');
  const [expandedCategories, setExpandedCategories] = useState<string[]>([]);
  const { policies } = useRetentionPolicies();

  const allControls = useMemo(() => {
    const controls = [
      ...SOC2_CONTROLS,
      ...GDPR_CONTROLS,
      ...HIPAA_CONTROLS.map(c => ({
        ...c,
        category: c.safeguardType
          ? `${c.safeguardType.charAt(0).toUpperCase()}${c.safeguardType.slice(1)} Safeguards`
          : c.category,
      })),
    ];

    if (selectedFramework === 'all') return controls;
    return controls.filter(c => c.framework === selectedFramework);
  }, [selectedFramework]);

  const stats = useMemo(() => {
    const total = allControls.length;
    const compliant = allControls.filter(c => c.status === 'compliant').length;
    const partial = allControls.filter(c => c.status === 'partial').length;
    const nonCompliant = allControls.filter(c => c.status === 'non_compliant').length;

    return {
      total,
      compliant,
      partial,
      nonCompliant,
      complianceRate: Math.round((compliant / total) * 100),
    };
  }, [allControls]);

  const groupedControls = useMemo(() => {
    const groups: Record<string, ComplianceControl[]> = {};
    for (const control of allControls) {
      const key = `${control.framework}-${control.category}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(control);
    }
    return groups;
  }, [allControls]);

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Compliance Dashboard
          </h2>
          <p className="text-sm text-muted-foreground">
            SOC2, HIPAA, and GDPR compliance status
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Framework Filter */}
      <div className="flex items-center gap-2">
        {(['all', 'SOC2', 'HIPAA', 'GDPR'] as const).map((framework) => (
          <Button
            key={framework}
            variant={selectedFramework === framework ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedFramework(framework)}
          >
            {framework === 'all' ? 'All Frameworks' : framework}
          </Button>
        ))}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
          label="Compliant"
          value={stats.compliant}
          total={stats.total}
          color="green"
        />
        <StatCard
          icon={<AlertTriangle className="h-5 w-5 text-yellow-500" />}
          label="Partial"
          value={stats.partial}
          total={stats.total}
          color="yellow"
        />
        <StatCard
          icon={<XCircle className="h-5 w-5 text-red-500" />}
          label="Non-Compliant"
          value={stats.nonCompliant}
          total={stats.total}
          color="red"
        />
        <StatCard
          icon={<Shield className="h-5 w-5 text-primary" />}
          label="Compliance Rate"
          value={`${stats.complianceRate}%`}
          color="primary"
        />
      </div>

      {/* Controls by Category */}
      <div className="space-y-4">
        <h3 className="font-semibold">Controls by Category</h3>

        <div className="space-y-2">
          {Object.entries(groupedControls).map(([key, controls]) => {
            const [framework, category] = key.split('-');
            const isExpanded = expandedCategories.includes(key);
            const categoryStats = {
              compliant: controls.filter(c => c.status === 'compliant').length,
              total: controls.length,
            };

            return (
              <div key={key} className="border rounded-lg overflow-hidden">
                <button
                  className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
                  onClick={() => toggleCategory(key)}
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <span className="text-xs font-medium px-2 py-0.5 rounded bg-primary/10 text-primary">
                      {framework}
                    </span>
                    <span className="font-medium">{category}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {categoryStats.compliant}/{categoryStats.total} compliant
                    </span>
                    <ComplianceIndicator
                      rate={categoryStats.compliant / categoryStats.total}
                    />
                  </div>
                </button>

                {isExpanded && (
                  <div className="border-t divide-y">
                    {controls.map((control) => (
                      <ControlRow key={control.id} control={control} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Data Retention Summary */}
      <div className="space-y-4">
        <h3 className="font-semibold">Data Retention Policies</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {policies.slice(0, 6).map((policy) => (
            <div key={policy.id} className="p-4 rounded-lg border">
              <div className="flex items-center gap-2 mb-2">
                <Database className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">{policy.dataCategory}</span>
              </div>
              <p className="text-xs text-muted-foreground mb-2">
                {policy.description}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-sm">
                  {formatRetentionPeriod(policy.retentionPeriod)}
                </span>
                <div className="flex gap-1">
                  {policy.framework.map((f) => (
                    <span
                      key={f}
                      className="text-xs px-1.5 py-0.5 rounded bg-muted"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  total?: number;
  color: 'green' | 'yellow' | 'red' | 'primary';
}

function StatCard({ icon, label, value, total, color }: StatCardProps) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={cn(
          'text-2xl font-bold',
          color === 'green' && 'text-green-600',
          color === 'yellow' && 'text-yellow-600',
          color === 'red' && 'text-red-600',
          color === 'primary' && 'text-primary'
        )}>
          {value}
        </span>
        {total !== undefined && (
          <span className="text-sm text-muted-foreground">/ {total}</span>
        )}
      </div>
    </div>
  );
}

function ComplianceIndicator({ rate }: { rate: number }) {
  const percentage = Math.round(rate * 100);

  return (
    <div className="w-16 h-2 rounded-full bg-muted overflow-hidden">
      <div
        className={cn(
          'h-full rounded-full transition-all',
          percentage === 100 && 'bg-green-500',
          percentage >= 80 && percentage < 100 && 'bg-yellow-500',
          percentage < 80 && 'bg-red-500'
        )}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

function ControlRow({ control }: { control: ComplianceControl }) {
  const statusIcons = {
    compliant: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    partial: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    non_compliant: <XCircle className="h-4 w-4 text-red-500" />,
    not_applicable: <Clock className="h-4 w-4 text-gray-400" />,
  };

  return (
    <div className="flex items-center justify-between p-4 hover:bg-muted/30">
      <div className="flex items-center gap-3">
        {statusIcons[control.status]}
        <div>
          <span className="font-medium text-sm">{control.name}</span>
          <p className="text-xs text-muted-foreground">{control.description}</p>
        </div>
      </div>
      <span className="text-xs text-muted-foreground">{control.id}</span>
    </div>
  );
}

// =============================================================================
// FRAMEWORK OVERVIEW CARDS
// =============================================================================

export function FrameworkOverviewCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <FrameworkCard
        framework="SOC2"
        icon={<Building2 className="h-6 w-6" />}
        description="Service Organization Control 2 - Security, Availability, Processing Integrity, Confidentiality, Privacy"
        controlCount={SOC2_CONTROLS.length}
        status="compliant"
      />
      <FrameworkCard
        framework="HIPAA"
        icon={<Lock className="h-6 w-6" />}
        description="Health Insurance Portability and Accountability Act - PHI Protection"
        controlCount={HIPAA_CONTROLS.length}
        status="compliant"
      />
      <FrameworkCard
        framework="GDPR"
        icon={<Eye className="h-6 w-6" />}
        description="General Data Protection Regulation - EU Data Privacy"
        controlCount={GDPR_CONTROLS.length}
        status="compliant"
      />
    </div>
  );
}

interface FrameworkCardProps {
  framework: ComplianceFramework;
  icon: React.ReactNode;
  description: string;
  controlCount: number;
  status: ComplianceStatus;
}

function FrameworkCard({
  framework,
  icon,
  description,
  controlCount,
  status,
}: FrameworkCardProps) {
  return (
    <div className="p-6 rounded-lg border bg-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
          <h3 className="font-semibold">{framework}</h3>
        </div>
        <StatusBadge status={status} />
      </div>
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{controlCount} controls</span>
        <Button variant="link" size="sm" className="h-auto p-0">
          View Details
        </Button>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: ComplianceStatus }) {
  const config = {
    compliant: { label: 'Compliant', className: 'bg-green-100 text-green-700' },
    partial: { label: 'Partial', className: 'bg-yellow-100 text-yellow-700' },
    non_compliant: { label: 'Non-Compliant', className: 'bg-red-100 text-red-700' },
    not_applicable: { label: 'N/A', className: 'bg-gray-100 text-gray-700' },
  }[status];

  return (
    <span className={cn('text-xs font-medium px-2 py-1 rounded', config.className)}>
      {config.label}
    </span>
  );
}
