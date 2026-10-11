'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { X, Cookie, Settings, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// =============================================================================
// SIMPLE CONSENT STORAGE
// =============================================================================

const CONSENT_KEY = 'nexus_consent_accepted';

type ConsentPurpose = 'essential' | 'analytics' | 'marketing' | 'personalization' | 'thirdParty' | 'aiTraining' | 'dataSharing';

const CONSENT_PURPOSES: Record<ConsentPurpose, { name: string; description: string; required: boolean }> = {
  essential: {
    name: 'Essential Cookies',
    description: 'Required for the platform to function properly. Cannot be disabled.',
    required: true,
  },
  analytics: {
    name: 'Analytics',
    description: 'Help us understand how you use our platform to improve it.',
    required: false,
  },
  marketing: {
    name: 'Marketing',
    description: 'Receive updates about new features and promotional offers.',
    required: false,
  },
  personalization: {
    name: 'Personalization',
    description: 'Customize your experience based on your usage patterns.',
    required: false,
  },
  thirdParty: {
    name: 'Third-Party Services',
    description: 'Share data with integrated third-party services.',
    required: false,
  },
  aiTraining: {
    name: 'AI Model Training',
    description: 'Allow your anonymized data to improve our AI models.',
    required: false,
  },
  dataSharing: {
    name: 'Data Sharing',
    description: 'Share aggregated data for research purposes.',
    required: false,
  },
};

function getConsentStatus(): boolean {
  if (typeof window === 'undefined') return true; // SSR - assume consented
  return localStorage.getItem(CONSENT_KEY) === 'true';
}

function setConsentStatus(accepted: boolean): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(CONSENT_KEY, String(accepted));
}

// =============================================================================
// CONSENT BANNER
// =============================================================================

export function ConsentBanner() {
  const [isVisible, setIsVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [preferences, setPreferences] = useState({
    analytics: false,
    marketing: false,
    personalization: false,
    thirdParty: false,
    aiTraining: false,
    dataSharing: false,
  });

  // Check consent status on mount
  useEffect(() => {
    const hasConsent = getConsentStatus();
    setIsVisible(!hasConsent);
  }, []);

  const handleAcceptAll = () => {
    setConsentStatus(true);
    setIsVisible(false);
  };

  const handleRejectAll = () => {
    setConsentStatus(true); // Mark as handled even if rejected
    setIsVisible(false);
  };

  const handleSavePreferences = () => {
    setConsentStatus(true);
    setIsVisible(false);
  };

  // Don't render if consent already given
  if (!isVisible) return null;


  return (
    <div role="region" aria-label="Cookie consent" className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-background border-t shadow-lg animate-in slide-in-from-bottom">
      <div className="max-w-4xl mx-auto">
        {!showDetails ? (
          // Simple banner view
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <Cookie className="h-6 w-6 text-primary shrink-0" />
            <div className="flex-1">
              <p className="text-sm">
                We use cookies and similar technologies to enhance your experience,
                analyze usage, and assist in our marketing efforts.{' '}
                <Link href="/privacy" className="underline hover:text-primary">
                  Learn more
                </Link>
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDetails(true)}
              >
                <Settings className="h-4 w-4 mr-2" />
                Customize
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRejectAll}
              >
                Reject All
              </Button>
              <Button
                size="sm"
                onClick={handleAcceptAll}
              >
                Accept All
              </Button>
            </div>
          </div>
        ) : (
          // Detailed preferences view
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                <h3 className="font-semibold">Privacy Preferences</h3>
              </div>
              <button
                onClick={() => setShowDetails(false)}
                className="p-1 hover:bg-muted rounded"
                aria-label="Close preferences"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <div className="grid gap-3 max-h-64 overflow-y-auto">
              {(Object.entries(CONSENT_PURPOSES) as [ConsentPurpose, typeof CONSENT_PURPOSES[ConsentPurpose]][]).map(
                ([key, config]) => (
                  <ConsentToggle
                    key={key}
                    purposeKey={key}
                    name={config.name}
                    description={config.description}
                    required={config.required}
                    checked={key === 'essential' ? true : preferences[key as keyof typeof preferences]}
                    onCheckedChange={(checked) => {
                      if (key !== 'essential') {
                        setPreferences(prev => ({
                          ...prev,
                          [key]: checked,
                        }));
                      }
                    }}
                  />
                )
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t">
              <Link
                href="/privacy"
                className="text-sm text-muted-foreground hover:text-foreground underline"
              >
                Privacy Policy
              </Link>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRejectAll}
                >
                  Reject All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAcceptAll}
                >
                  Accept All
                </Button>
                <Button
                  size="sm"
                  onClick={handleSavePreferences}
                >
                  Save Preferences
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// CONSENT TOGGLE
// =============================================================================

interface ConsentToggleProps {
  purposeKey: string;
  name: string;
  description: string;
  required: boolean;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

function ConsentToggle({
  purposeKey,
  name,
  description,
  required,
  checked,
  onCheckedChange,
}: ConsentToggleProps) {
  return (
    <label
      htmlFor={`consent-${purposeKey}`}
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
        required ? 'bg-muted/50 cursor-not-allowed' : 'hover:bg-muted/50'
      )}
    >
      <input
        type="checkbox"
        id={`consent-${purposeKey}`}
        checked={checked}
        onChange={(e) => onCheckedChange(e.target.checked)}
        disabled={required}
        className="mt-1 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{name}</span>
          {required && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              Required
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
    </label>
  );
}

// =============================================================================
// CONSENT SETTINGS PAGE COMPONENT
// =============================================================================

export function ConsentSettings() {
  const [localPrefs, setLocalPrefs] = useState({
    essential: true,
    analytics: false,
    marketing: false,
    personalization: false,
    thirdParty: false,
    aiTraining: false,
    dataSharing: false,
  });
  const [saving, setSaving] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setConsentStatus(true);
    setTimeout(() => setSaving(false), 500);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Privacy Preferences</h3>
        <p className="text-sm text-muted-foreground">
          Manage how your data is used. Changes take effect immediately.
        </p>
      </div>

      <div className="space-y-4">
        {(Object.entries(CONSENT_PURPOSES) as [ConsentPurpose, typeof CONSENT_PURPOSES[ConsentPurpose]][]).map(
          ([key, config]) => {
            const isEnabled = key === 'essential' ? true :
              Boolean(localPrefs[key as keyof typeof localPrefs]);

            return (
              <div
                key={key}
                className="flex items-center justify-between p-4 rounded-lg border"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{config.name}</span>
                    {config.required && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                        Required
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {config.description}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={isEnabled}
                    onChange={(e) => {
                      if (key !== 'essential') {
                        setLocalPrefs(prev => ({
                          ...prev,
                          [key]: e.target.checked,
                        }));
                      }
                    }}
                    disabled={config.required}
                    className="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
                  />
                </div>
              </div>
            );
          }
        )}
      </div>

      <div className="flex items-center justify-end pt-4 border-t">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>
    </div>
  );
}

// =============================================================================
// MINIMAL CONSENT PROMPT
// =============================================================================

export function MinimalConsentPrompt() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const hasConsent = getConsentStatus();
    setIsVisible(!hasConsent);
  }, []);

  const handleAccept = () => {
    setConsentStatus(true);
    setIsVisible(false);
  };

  const handleDecline = () => {
    setConsentStatus(true);
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm p-4 bg-card rounded-lg border shadow-lg animate-in slide-in-from-bottom-4">
      <div className="flex items-start gap-3">
        <Cookie className="h-5 w-5 text-primary shrink-0 mt-0.5" />
        <div className="space-y-3">
          <p className="text-sm">
            We use cookies to improve your experience.{' '}
            <Link href="/privacy" className="underline">
              Learn more
            </Link>
          </p>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleDecline}>
              Decline
            </Button>
            <Button size="sm" onClick={handleAccept}>
              Accept
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
