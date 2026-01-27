/**
 * ConsentBanner Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock ConsentBanner component
interface ConsentBannerProps {
  isVisible?: boolean;
  onAcceptAll?: () => void;
  onRejectAll?: () => void;
  onCustomize?: () => void;
  onClose?: () => void;
  privacyPolicyUrl?: string;
}

const ConsentBanner = ({
  isVisible = true,
  onAcceptAll,
  onRejectAll,
  onCustomize,
  onClose,
  privacyPolicyUrl = '/privacy',
}: ConsentBannerProps) => {
  if (!isVisible) return null;

  return (
    <div data-testid="consent-banner" className="consent-banner" role="dialog" aria-label="Cookie consent">
      <div className="content">
        <h2>We value your privacy</h2>
        <p data-testid="consent-message">
          We use cookies to enhance your browsing experience, serve personalized content, and analyze our traffic.
          By clicking "Accept All", you consent to our use of cookies.
        </p>
        <a href={privacyPolicyUrl} data-testid="privacy-link">
          Privacy Policy
        </a>
      </div>
      <div className="actions">
        <button data-testid="accept-all" onClick={onAcceptAll}>
          Accept All
        </button>
        <button data-testid="reject-all" onClick={onRejectAll}>
          Reject All
        </button>
        <button data-testid="customize" onClick={onCustomize}>
          Customize
        </button>
      </div>
      <button data-testid="close-banner" onClick={onClose} aria-label="Close">
        ×
      </button>
    </div>
  );
};

describe('ConsentBanner', () => {
  it('renders consent banner when visible', () => {
    render(<ConsentBanner isVisible={true} />);
    expect(screen.getByTestId('consent-banner')).toBeInTheDocument();
  });

  it('does not render when not visible', () => {
    render(<ConsentBanner isVisible={false} />);
    expect(screen.queryByTestId('consent-banner')).not.toBeInTheDocument();
  });

  it('displays consent message', () => {
    render(<ConsentBanner />);
    expect(screen.getByTestId('consent-message')).toBeInTheDocument();
    expect(screen.getByText(/We use cookies/)).toBeInTheDocument();
  });

  it('renders privacy policy link', () => {
    render(<ConsentBanner privacyPolicyUrl="/custom-privacy" />);
    const link = screen.getByTestId('privacy-link');
    expect(link).toHaveAttribute('href', '/custom-privacy');
  });

  it('renders accept all button', () => {
    render(<ConsentBanner />);
    expect(screen.getByTestId('accept-all')).toHaveTextContent('Accept All');
  });

  it('renders reject all button', () => {
    render(<ConsentBanner />);
    expect(screen.getByTestId('reject-all')).toHaveTextContent('Reject All');
  });

  it('renders customize button', () => {
    render(<ConsentBanner />);
    expect(screen.getByTestId('customize')).toHaveTextContent('Customize');
  });

  it('renders close button', () => {
    render(<ConsentBanner />);
    expect(screen.getByTestId('close-banner')).toBeInTheDocument();
  });

  it('calls onAcceptAll when accept button is clicked', () => {
    const onAcceptAll = vi.fn();
    render(<ConsentBanner onAcceptAll={onAcceptAll} />);
    
    fireEvent.click(screen.getByTestId('accept-all'));
    
    expect(onAcceptAll).toHaveBeenCalled();
  });

  it('calls onRejectAll when reject button is clicked', () => {
    const onRejectAll = vi.fn();
    render(<ConsentBanner onRejectAll={onRejectAll} />);
    
    fireEvent.click(screen.getByTestId('reject-all'));
    
    expect(onRejectAll).toHaveBeenCalled();
  });

  it('calls onCustomize when customize button is clicked', () => {
    const onCustomize = vi.fn();
    render(<ConsentBanner onCustomize={onCustomize} />);
    
    fireEvent.click(screen.getByTestId('customize'));
    
    expect(onCustomize).toHaveBeenCalled();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<ConsentBanner onClose={onClose} />);
    
    fireEvent.click(screen.getByTestId('close-banner'));
    
    expect(onClose).toHaveBeenCalled();
  });

  it('has correct accessibility attributes', () => {
    render(<ConsentBanner />);
    const banner = screen.getByTestId('consent-banner');
    expect(banner).toHaveAttribute('role', 'dialog');
    expect(banner).toHaveAttribute('aria-label', 'Cookie consent');
  });

  it('close button has aria-label', () => {
    render(<ConsentBanner />);
    expect(screen.getByTestId('close-banner')).toHaveAttribute('aria-label', 'Close');
  });
});
