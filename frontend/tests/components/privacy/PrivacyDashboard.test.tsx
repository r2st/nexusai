/**
 * PrivacyDashboard Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock types
interface ConsentOption {
  id: string;
  name: string;
  description: string;
  required: boolean;
  enabled: boolean;
}

interface DataCategory {
  id: string;
  name: string;
  description: string;
  dataTypes: string[];
  retentionPeriod: string;
}

interface PrivacyDashboardProps {
  consentOptions?: ConsentOption[];
  dataCategories?: DataCategory[];
  onConsentChange?: (id: string, enabled: boolean) => void;
  onExportData?: () => void;
  onDeleteData?: () => void;
  onRequestAccess?: () => void;
}

const mockConsents: ConsentOption[] = [
  { id: 'essential', name: 'Essential', description: 'Required for app functionality', required: true, enabled: true },
  { id: 'analytics', name: 'Analytics', description: 'Help us improve', required: false, enabled: true },
  { id: 'marketing', name: 'Marketing', description: 'Personalized content', required: false, enabled: false },
];

const mockCategories: DataCategory[] = [
  { id: 'profile', name: 'Profile Data', description: 'Your account info', dataTypes: ['Name', 'Email'], retentionPeriod: '2 years' },
  { id: 'usage', name: 'Usage Data', description: 'How you use the app', dataTypes: ['Pages visited', 'Features used'], retentionPeriod: '1 year' },
];

// Mock PrivacyDashboard component
const PrivacyDashboard = ({
  consentOptions = mockConsents,
  dataCategories = mockCategories,
  onConsentChange,
  onExportData,
  onDeleteData,
  onRequestAccess,
}: PrivacyDashboardProps) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false);

  return (
    <div data-testid="privacy-dashboard" className="privacy-dashboard">
      <h1>Privacy Settings</h1>
      
      <section data-testid="consent-section">
        <h2>Consent Preferences</h2>
        {consentOptions.map((option) => (
          <div key={option.id} data-testid={`consent-${option.id}`} className="consent-item">
            <div>
              <strong>{option.name}</strong>
              <p>{option.description}</p>
              {option.required && <span data-testid={`required-${option.id}`}>Required</span>}
            </div>
            <input
              type="checkbox"
              data-testid={`toggle-${option.id}`}
              checked={option.enabled}
              disabled={option.required}
              onChange={(e) => onConsentChange?.(option.id, e.target.checked)}
            />
          </div>
        ))}
      </section>

      <section data-testid="data-section">
        <h2>Your Data</h2>
        {dataCategories.map((category) => (
          <div key={category.id} data-testid={`category-${category.id}`} className="data-category">
            <h3>{category.name}</h3>
            <p>{category.description}</p>
            <ul>
              {category.dataTypes.map((type) => (
                <li key={type}>{type}</li>
              ))}
            </ul>
            <span>Retention: {category.retentionPeriod}</span>
          </div>
        ))}
      </section>

      <section data-testid="actions-section">
        <h2>Data Rights</h2>
        <button data-testid="export-data" onClick={onExportData}>
          Export My Data
        </button>
        <button data-testid="request-access" onClick={onRequestAccess}>
          Request Data Access
        </button>
        <button data-testid="delete-data" onClick={() => setShowDeleteConfirm(true)}>
          Delete My Data
        </button>
      </section>

      {showDeleteConfirm && (
        <div data-testid="delete-confirm-dialog" className="confirm-dialog">
          <p>Are you sure you want to delete all your data? This action cannot be undone.</p>
          <button data-testid="confirm-delete" onClick={() => {
            onDeleteData?.();
            setShowDeleteConfirm(false);
          }}>
            Yes, Delete
          </button>
          <button data-testid="cancel-delete" onClick={() => setShowDeleteConfirm(false)}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
};

describe('PrivacyDashboard', () => {
  it('renders privacy dashboard', () => {
    render(<PrivacyDashboard />);
    expect(screen.getByTestId('privacy-dashboard')).toBeInTheDocument();
  });

  it('renders consent section', () => {
    render(<PrivacyDashboard />);
    expect(screen.getByTestId('consent-section')).toBeInTheDocument();
  });

  it('renders all consent options', () => {
    render(<PrivacyDashboard consentOptions={mockConsents} />);
    expect(screen.getByTestId('consent-essential')).toBeInTheDocument();
    expect(screen.getByTestId('consent-analytics')).toBeInTheDocument();
    expect(screen.getByTestId('consent-marketing')).toBeInTheDocument();
  });

  it('shows required badge for required consents', () => {
    render(<PrivacyDashboard consentOptions={mockConsents} />);
    expect(screen.getByTestId('required-essential')).toBeInTheDocument();
    expect(screen.queryByTestId('required-analytics')).not.toBeInTheDocument();
  });

  it('disables toggle for required consents', () => {
    render(<PrivacyDashboard consentOptions={mockConsents} />);
    expect(screen.getByTestId('toggle-essential')).toBeDisabled();
    expect(screen.getByTestId('toggle-analytics')).not.toBeDisabled();
  });

  it('calls onConsentChange when toggle is clicked', () => {
    const onConsentChange = vi.fn();
    render(<PrivacyDashboard consentOptions={mockConsents} onConsentChange={onConsentChange} />);
    
    fireEvent.click(screen.getByTestId('toggle-analytics'));
    
    expect(onConsentChange).toHaveBeenCalledWith('analytics', false);
  });

  it('renders data categories section', () => {
    render(<PrivacyDashboard dataCategories={mockCategories} />);
    expect(screen.getByTestId('data-section')).toBeInTheDocument();
    expect(screen.getByTestId('category-profile')).toBeInTheDocument();
    expect(screen.getByTestId('category-usage')).toBeInTheDocument();
  });

  it('displays data types for each category', () => {
    render(<PrivacyDashboard dataCategories={mockCategories} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  it('displays retention period', () => {
    render(<PrivacyDashboard dataCategories={mockCategories} />);
    expect(screen.getByText('Retention: 2 years')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    render(<PrivacyDashboard />);
    expect(screen.getByTestId('export-data')).toBeInTheDocument();
    expect(screen.getByTestId('request-access')).toBeInTheDocument();
    expect(screen.getByTestId('delete-data')).toBeInTheDocument();
  });

  it('calls onExportData when export button is clicked', () => {
    const onExportData = vi.fn();
    render(<PrivacyDashboard onExportData={onExportData} />);
    
    fireEvent.click(screen.getByTestId('export-data'));
    
    expect(onExportData).toHaveBeenCalled();
  });

  it('calls onRequestAccess when access button is clicked', () => {
    const onRequestAccess = vi.fn();
    render(<PrivacyDashboard onRequestAccess={onRequestAccess} />);
    
    fireEvent.click(screen.getByTestId('request-access'));
    
    expect(onRequestAccess).toHaveBeenCalled();
  });

  it('shows confirmation dialog when delete is clicked', () => {
    render(<PrivacyDashboard />);
    
    fireEvent.click(screen.getByTestId('delete-data'));
    
    expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
  });

  it('calls onDeleteData when confirmed', () => {
    const onDeleteData = vi.fn();
    render(<PrivacyDashboard onDeleteData={onDeleteData} />);
    
    fireEvent.click(screen.getByTestId('delete-data'));
    fireEvent.click(screen.getByTestId('confirm-delete'));
    
    expect(onDeleteData).toHaveBeenCalled();
  });

  it('closes dialog when cancel is clicked', () => {
    render(<PrivacyDashboard />);
    
    fireEvent.click(screen.getByTestId('delete-data'));
    fireEvent.click(screen.getByTestId('cancel-delete'));
    
    expect(screen.queryByTestId('delete-confirm-dialog')).not.toBeInTheDocument();
  });
});
