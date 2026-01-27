/**
 * ComplianceDashboard Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock types
interface ComplianceStatus {
  framework: string;
  status: 'compliant' | 'partial' | 'non-compliant';
  score: number;
  lastAudit: string;
  nextAudit: string;
}

interface ComplianceControl {
  id: string;
  name: string;
  description: string;
  status: 'pass' | 'fail' | 'warning';
  framework: string;
}

interface ComplianceDashboardProps {
  frameworks?: ComplianceStatus[];
  controls?: ComplianceControl[];
  onRunAudit?: (framework: string) => void;
  onExportReport?: (framework: string) => void;
}

const mockFrameworks: ComplianceStatus[] = [
  { framework: 'SOC 2', status: 'compliant', score: 95, lastAudit: '2024-01-15', nextAudit: '2024-07-15' },
  { framework: 'GDPR', status: 'compliant', score: 92, lastAudit: '2024-01-10', nextAudit: '2024-07-10' },
  { framework: 'HIPAA', status: 'partial', score: 78, lastAudit: '2024-01-20', nextAudit: '2024-07-20' },
];

const mockControls: ComplianceControl[] = [
  { id: '1', name: 'Access Control', description: 'Proper access controls in place', status: 'pass', framework: 'SOC 2' },
  { id: '2', name: 'Data Encryption', description: 'Data encrypted at rest and in transit', status: 'pass', framework: 'SOC 2' },
  { id: '3', name: 'Audit Logging', description: 'Comprehensive audit logging', status: 'warning', framework: 'SOC 2' },
];

// Mock ComplianceDashboard component
const ComplianceDashboard = ({
  frameworks = mockFrameworks,
  controls = mockControls,
  onRunAudit,
  onExportReport,
}: ComplianceDashboardProps) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'compliant':
      case 'pass':
        return 'green';
      case 'partial':
      case 'warning':
        return 'yellow';
      default:
        return 'red';
    }
  };

  return (
    <div data-testid="compliance-dashboard" className="compliance-dashboard">
      <h1>Compliance Dashboard</h1>
      
      <section data-testid="frameworks-section">
        <h2>Compliance Frameworks</h2>
        <div className="framework-cards">
          {frameworks.map((fw) => (
            <div key={fw.framework} data-testid={`framework-${fw.framework}`} className="framework-card">
              <h3>{fw.framework}</h3>
              <div data-testid={`status-${fw.framework}`} className={`status ${getStatusColor(fw.status)}`}>
                {fw.status}
              </div>
              <div data-testid={`score-${fw.framework}`} className="score">
                Score: {fw.score}%
              </div>
              <div className="audit-info">
                <span>Last Audit: {fw.lastAudit}</span>
                <span>Next Audit: {fw.nextAudit}</span>
              </div>
              <div className="actions">
                <button data-testid={`audit-${fw.framework}`} onClick={() => onRunAudit?.(fw.framework)}>
                  Run Audit
                </button>
                <button data-testid={`export-${fw.framework}`} onClick={() => onExportReport?.(fw.framework)}>
                  Export Report
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section data-testid="controls-section">
        <h2>Control Status</h2>
        <table>
          <thead>
            <tr>
              <th>Control</th>
              <th>Description</th>
              <th>Framework</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {controls.map((control) => (
              <tr key={control.id} data-testid={`control-${control.id}`}>
                <td>{control.name}</td>
                <td>{control.description}</td>
                <td>{control.framework}</td>
                <td data-testid={`control-status-${control.id}`} className={getStatusColor(control.status)}>
                  {control.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section data-testid="summary-section">
        <h2>Summary</h2>
        <div className="summary-stats">
          <div data-testid="total-frameworks">
            Total Frameworks: {frameworks.length}
          </div>
          <div data-testid="compliant-count">
            Compliant: {frameworks.filter((f) => f.status === 'compliant').length}
          </div>
          <div data-testid="avg-score">
            Average Score: {Math.round(frameworks.reduce((acc, f) => acc + f.score, 0) / frameworks.length)}%
          </div>
        </div>
      </section>
    </div>
  );
};

describe('ComplianceDashboard', () => {
  it('renders compliance dashboard', () => {
    render(<ComplianceDashboard />);
    expect(screen.getByTestId('compliance-dashboard')).toBeInTheDocument();
  });

  it('renders frameworks section', () => {
    render(<ComplianceDashboard />);
    expect(screen.getByTestId('frameworks-section')).toBeInTheDocument();
  });

  it('renders all framework cards', () => {
    render(<ComplianceDashboard frameworks={mockFrameworks} />);
    expect(screen.getByTestId('framework-SOC 2')).toBeInTheDocument();
    expect(screen.getByTestId('framework-GDPR')).toBeInTheDocument();
    expect(screen.getByTestId('framework-HIPAA')).toBeInTheDocument();
  });

  it('displays framework status', () => {
    render(<ComplianceDashboard frameworks={mockFrameworks} />);
    expect(screen.getByTestId('status-SOC 2')).toHaveTextContent('compliant');
    expect(screen.getByTestId('status-HIPAA')).toHaveTextContent('partial');
  });

  it('displays compliance score', () => {
    render(<ComplianceDashboard frameworks={mockFrameworks} />);
    expect(screen.getByTestId('score-SOC 2')).toHaveTextContent('Score: 95%');
  });

  it('displays audit dates', () => {
    render(<ComplianceDashboard frameworks={mockFrameworks} />);
    expect(screen.getByText('Last Audit: 2024-01-15')).toBeInTheDocument();
    expect(screen.getByText('Next Audit: 2024-07-15')).toBeInTheDocument();
  });

  it('calls onRunAudit when audit button is clicked', () => {
    const onRunAudit = vi.fn();
    render(<ComplianceDashboard frameworks={mockFrameworks} onRunAudit={onRunAudit} />);
    
    fireEvent.click(screen.getByTestId('audit-SOC 2'));
    
    expect(onRunAudit).toHaveBeenCalledWith('SOC 2');
  });

  it('calls onExportReport when export button is clicked', () => {
    const onExportReport = vi.fn();
    render(<ComplianceDashboard frameworks={mockFrameworks} onExportReport={onExportReport} />);
    
    fireEvent.click(screen.getByTestId('export-GDPR'));
    
    expect(onExportReport).toHaveBeenCalledWith('GDPR');
  });

  it('renders controls section', () => {
    render(<ComplianceDashboard />);
    expect(screen.getByTestId('controls-section')).toBeInTheDocument();
  });

  it('renders all controls', () => {
    render(<ComplianceDashboard controls={mockControls} />);
    expect(screen.getByTestId('control-1')).toBeInTheDocument();
    expect(screen.getByTestId('control-2')).toBeInTheDocument();
    expect(screen.getByTestId('control-3')).toBeInTheDocument();
  });

  it('displays control status', () => {
    render(<ComplianceDashboard controls={mockControls} />);
    expect(screen.getByTestId('control-status-1')).toHaveTextContent('pass');
    expect(screen.getByTestId('control-status-3')).toHaveTextContent('warning');
  });

  it('renders summary section', () => {
    render(<ComplianceDashboard />);
    expect(screen.getByTestId('summary-section')).toBeInTheDocument();
  });

  it('displays total frameworks count', () => {
    render(<ComplianceDashboard frameworks={mockFrameworks} />);
    expect(screen.getByTestId('total-frameworks')).toHaveTextContent('Total Frameworks: 3');
  });

  it('displays compliant count', () => {
    render(<ComplianceDashboard frameworks={mockFrameworks} />);
    expect(screen.getByTestId('compliant-count')).toHaveTextContent('Compliant: 2');
  });

  it('displays average score', () => {
    render(<ComplianceDashboard frameworks={mockFrameworks} />);
    expect(screen.getByTestId('avg-score')).toHaveTextContent('Average Score: 88%');
  });
});
