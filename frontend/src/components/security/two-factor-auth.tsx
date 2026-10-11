'use client';

/**
 * Two-Factor Authentication Components
 * 
 * Provides UI for setting up, verifying, and managing 2FA.
 * Supports TOTP (authenticator apps) and backup codes.
 */

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import {
  Shield,
  Smartphone,
  Key,
  Copy,
  Check,
  AlertTriangle,
  Loader2,
  QrCode,
  Download,
  Eye,
  EyeOff,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api, getApiErrorMessage } from '@/lib/api';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// =============================================================================
// TYPES
// =============================================================================

interface TwoFactorSetupData {
  secret: string;
  qr_code_url: string;
  backup_codes: string[];
}

interface TwoFactorStatus {
  enabled: boolean;
  method: 'totp' | 'sms' | null;
  backup_codes_remaining: number;
  last_used: string | null;
}

// =============================================================================
// 2FA SETUP WIZARD
// =============================================================================

interface TwoFactorSetupProps {
  onComplete: () => void;
  onCancel: () => void;
}

export function TwoFactorSetup({ onComplete, onCancel }: TwoFactorSetupProps) {
  const [step, setStep] = useState<'intro' | 'scan' | 'verify' | 'backup' | 'complete'>('intro');
  const [isLoading, setIsLoading] = useState(false);
  const [setupData, setSetupData] = useState<TwoFactorSetupData | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [downloadedBackup, setDownloadedBackup] = useState(false);

  // Start 2FA setup
  const initSetup = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post('/auth/2fa/setup');
      setSetupData(response.data);
      setStep('scan');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to initialize 2FA setup'));
    } finally {
      setIsLoading(false);
    }
  };

  // Verify the code
  const verifyCode = async () => {
    if (verificationCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await api.post('/auth/2fa/verify', { code: verificationCode });
      setStep('backup');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Invalid verification code'));
    } finally {
      setIsLoading(false);
    }
  };

  // Enable 2FA
  const enable2FA = async () => {
    setIsLoading(true);
    try {
      await api.post('/auth/2fa/enable');
      setStep('complete');
      toast.success('Two-factor authentication enabled');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to enable 2FA'));
    } finally {
      setIsLoading(false);
    }
  };

  // Copy secret to clipboard
  const copySecret = () => {
    if (setupData?.secret) {
      navigator.clipboard.writeText(setupData.secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
      toast.success('Secret copied to clipboard');
    }
  };

  // Download backup codes
  const downloadBackupCodes = () => {
    if (!setupData?.backup_codes) return;

    const content = `NexusAI Two-Factor Authentication Backup Codes
==============================================
Generated: ${new Date().toISOString()}

IMPORTANT: Keep these codes in a safe place.
Each code can only be used once.

${setupData.backup_codes.map((code, i) => `${i + 1}. ${code}`).join('\n')}

If you lose access to your authenticator app,
you can use one of these codes to sign in.
`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nexusai-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
    setDownloadedBackup(true);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="2fa-setup-title">
      <div className="bg-background rounded-lg border shadow-lg w-full max-w-lg p-6 mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Shield className="h-5 w-5 text-primary" aria-hidden="true" />
            </div>
            <div>
              <h2 id="2fa-setup-title" className="text-lg font-semibold">Set Up Two-Factor Authentication</h2>
              <p className="text-sm text-muted-foreground">
                Step {['intro', 'scan', 'verify', 'backup', 'complete'].indexOf(step) + 1} of 5
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onCancel} aria-label="Cancel setup">
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        {/* Progress */}
        <div className="h-1 bg-muted rounded-full mb-6 overflow-hidden" role="progressbar" aria-valuenow={(['intro', 'scan', 'verify', 'backup', 'complete'].indexOf(step) + 1) * 20} aria-valuemin={0} aria-valuemax={100} aria-label="Setup progress">
          <div
            className="h-full bg-primary transition-all"
            style={{
              width: `${((['intro', 'scan', 'verify', 'backup', 'complete'].indexOf(step) + 1) / 5) * 100}%`,
            }}
          />
        </div>

        {/* Error */}
        {error && (
          <div role="alert" className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Step: Introduction */}
        {step === 'intro' && (
          <div className="space-y-6">
            <div className="text-center">
              <Smartphone className="h-16 w-16 mx-auto text-primary mb-4" />
              <h3 className="text-xl font-semibold mb-2">Add Extra Security</h3>
              <p className="text-muted-foreground">
                Two-factor authentication adds an extra layer of security to your account
                by requiring a code from your phone in addition to your password.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                <QrCode className="h-5 w-5 text-primary mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Use an authenticator app</p>
                  <p className="text-xs text-muted-foreground">
                    Google Authenticator, Authy, or 1Password
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                <Key className="h-5 w-5 text-primary mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Get backup codes</p>
                  <p className="text-xs text-muted-foreground">
                    One-time use codes for account recovery
                  </p>
                </div>
              </div>
            </div>

            <Button className="w-full" onClick={initSetup} disabled={isLoading}>
              {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Get Started
            </Button>
          </div>
        )}

        {/* Step: Scan QR Code */}
        {step === 'scan' && setupData && (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-xl font-semibold mb-2">Scan QR Code</h3>
              <p className="text-muted-foreground text-sm">
                Open your authenticator app and scan this QR code
              </p>
            </div>

            {/* QR Code */}
            <div className="flex justify-center">
              <div className="p-4 bg-white rounded-lg">
                <img
                  src={setupData.qr_code_url}
                  alt="Scan this QR code with your authenticator app to set up two-factor authentication"
                  className="w-48 h-48"
                />
              </div>
            </div>

            {/* Manual entry */}
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground text-center">
                Or enter this code manually:
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-3 bg-muted rounded-lg font-mono text-sm break-all">
                  {setupData.secret}
                </code>
                <Button variant="outline" size="icon" onClick={copySecret} aria-label={copiedSecret ? 'Copied' : 'Copy secret key'}>
                  {copiedSecret ? (
                    <Check className="h-4 w-4 text-green-500" aria-hidden="true" />
                  ) : (
                    <Copy className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>
              </div>
            </div>

            <Button className="w-full" onClick={() => setStep('verify')}>
              I've Scanned the Code
            </Button>
          </div>
        )}

        {/* Step: Verify */}
        {step === 'verify' && (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-xl font-semibold mb-2">Verify Setup</h3>
              <p className="text-muted-foreground text-sm">
                Enter the 6-digit code from your authenticator app
              </p>
            </div>

            <OTPInput
              value={verificationCode}
              onChange={setVerificationCode}
              onComplete={verifyCode}
            />

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep('scan')}>
                Back
              </Button>
              <Button
                className="flex-1"
                onClick={verifyCode}
                disabled={isLoading || verificationCode.length !== 6}
              >
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Verify
              </Button>
            </div>
          </div>
        )}

        {/* Step: Backup Codes */}
        {step === 'backup' && setupData && (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-xl font-semibold mb-2">Save Backup Codes</h3>
              <p className="text-muted-foreground text-sm">
                Save these codes somewhere safe. You can use them to access your
                account if you lose your phone.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-muted/50 border">
              <div className="grid grid-cols-2 gap-2">
                {setupData.backup_codes.map((code, index) => (
                  <code
                    key={index}
                    className="p-2 bg-background rounded text-center font-mono text-sm"
                  >
                    {code}
                  </code>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <Button variant="outline" onClick={downloadBackupCodes} className="flex-1">
                <Download className="mr-2 h-4 w-4" />
                Download
              </Button>
              <Button
                onClick={() => {
                  navigator.clipboard.writeText(setupData.backup_codes.join('\n'));
                  toast.success('Backup codes copied');
                }}
                variant="outline"
                className="flex-1"
              >
                <Copy className="mr-2 h-4 w-4" />
                Copy All
              </Button>
            </div>

            <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
              <div className="flex gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600 shrink-0 mt-0.5" />
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  Each backup code can only be used once. Store them securely.
                </p>
              </div>
            </div>

            <Button
              className="w-full"
              onClick={enable2FA}
              disabled={isLoading || !downloadedBackup}
            >
              {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {downloadedBackup ? 'Enable Two-Factor Authentication' : 'Download Codes First'}
            </Button>
          </div>
        )}

        {/* Step: Complete */}
        {step === 'complete' && (
          <div className="space-y-6 text-center">
            <div className="h-16 w-16 mx-auto rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <Check className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-2">All Done!</h3>
              <p className="text-muted-foreground">
                Two-factor authentication is now enabled on your account.
                You'll need to enter a code from your authenticator app
                each time you sign in.
              </p>
            </div>
            <Button className="w-full" onClick={onComplete}>
              Done
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// OTP INPUT COMPONENT
// =============================================================================

interface OTPInputProps {
  value: string;
  onChange: (value: string) => void;
  onComplete?: () => void;
  length?: number;
  disabled?: boolean;
}

export function OTPInput({
  value,
  onChange,
  onComplete,
  length = 6,
  disabled = false,
}: OTPInputProps) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleChange = (index: number, char: string) => {
    if (!/^\d*$/.test(char)) return; // Only allow digits

    const newValue = value.split('');
    newValue[index] = char;
    const joined = newValue.join('').slice(0, length);
    onChange(joined);

    // Move to next input
    if (char && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }

    // Call onComplete when all digits entered
    if (joined.length === length && onComplete) {
      onComplete();
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !value[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    onChange(pasted);
    
    if (pasted.length === length && onComplete) {
      onComplete();
    }
  };

  return (
    <div className="flex justify-center gap-2" role="group" aria-label="Verification code">
      {Array.from({ length }).map((_, index) => (
        <input
          key={index}
          ref={(el) => {
            inputRefs.current[index] = el;
          }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={value[index] || ''}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={handlePaste}
          disabled={disabled}
          aria-label={`Digit ${index + 1} of ${length}`}
          autoComplete="one-time-code"
          className={cn(
            'w-12 h-14 text-center text-2xl font-mono rounded-lg border bg-background',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        />
      ))}
    </div>
  );
}

// =============================================================================
// 2FA VERIFICATION MODAL (for login)
// =============================================================================

interface TwoFactorVerifyProps {
  onVerify: (code: string) => Promise<void>;
  onCancel: () => void;
  onUseBackupCode: () => void;
}

export function TwoFactorVerify({ onVerify, onCancel, onUseBackupCode }: TwoFactorVerifyProps) {
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async () => {
    if (code.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await onVerify(code);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid code');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="2fa-verify-title">
      <div className="bg-background rounded-lg border shadow-lg w-full max-w-md p-6 mx-4">
        <div className="text-center mb-6">
          <div className="h-12 w-12 mx-auto rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <Shield className="h-6 w-6 text-primary" aria-hidden="true" />
          </div>
          <h2 id="2fa-verify-title" className="text-xl font-semibold">Two-Factor Authentication</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Enter the code from your authenticator app
          </p>
        </div>

        {error && (
          <div role="alert" className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        <OTPInput value={code} onChange={setCode} onComplete={handleVerify} />

        <div className="mt-6 space-y-3">
          <Button
            className="w-full"
            onClick={handleVerify}
            disabled={isLoading || code.length !== 6}
          >
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Verify
          </Button>
          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={onCancel}>
              Cancel
            </Button>
            <Button variant="ghost" className="flex-1" onClick={onUseBackupCode}>
              Use Backup Code
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// BACKUP CODE INPUT
// =============================================================================

interface BackupCodeInputProps {
  onVerify: (code: string) => Promise<void>;
  onCancel: () => void;
  onBack: () => void;
}

export function BackupCodeInput({ onVerify, onCancel, onBack }: BackupCodeInputProps) {
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async () => {
    if (code.length < 8) {
      setError('Please enter a valid backup code');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await onVerify(code.replace(/\s/g, ''));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid backup code');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="backup-code-title">
      <div className="bg-background rounded-lg border shadow-lg w-full max-w-md p-6 mx-4">
        <div className="text-center mb-6">
          <div className="h-12 w-12 mx-auto rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <Key className="h-6 w-6 text-primary" aria-hidden="true" />
          </div>
          <h2 id="backup-code-title" className="text-xl font-semibold">Use Backup Code</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Enter one of your backup codes
          </p>
        </div>

        {error && (
          <div role="alert" className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        <Input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="XXXX-XXXX"
          aria-label="Backup code"
          className="text-center font-mono text-lg"
        />

        <div className="mt-6 space-y-3">
          <Button className="w-full" onClick={handleVerify} disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Verify
          </Button>
          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={onCancel}>
              Cancel
            </Button>
            <Button variant="ghost" className="flex-1" onClick={onBack}>
              Use Authenticator
            </Button>
          </div>
        </div>

        <p className="text-xs text-muted-foreground text-center mt-4">
          Each backup code can only be used once
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// 2FA STATUS CARD
// =============================================================================

interface TwoFactorStatusProps {
  onSetup: () => void;
  onDisable: () => void;
  onRegenerateCodes: () => void;
}

export function TwoFactorStatus({ onSetup, onDisable, onRegenerateCodes }: TwoFactorStatusProps) {
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const response = await api.get('/auth/2fa/status');
      setStatus(response.data);
    } catch (error) {
      // 2FA not set up
      setStatus({ enabled: false, method: null, backup_codes_remaining: 0, last_used: null });
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-lg border p-6">
        <div className="flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'h-10 w-10 rounded-full flex items-center justify-center',
              status?.enabled ? 'bg-green-100 dark:bg-green-900/30' : 'bg-muted'
            )}
          >
            <Shield
              className={cn(
                'h-5 w-5',
                status?.enabled ? 'text-green-600' : 'text-muted-foreground'
              )}
            />
          </div>
          <div>
            <h3 className="font-semibold">Two-Factor Authentication</h3>
            <p className="text-sm text-muted-foreground">
              {status?.enabled
                ? 'Your account is protected with 2FA'
                : 'Add an extra layer of security'}
            </p>
          </div>
        </div>
        <span
          className={cn(
            'px-2 py-1 rounded-full text-xs font-medium',
            status?.enabled
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-muted text-muted-foreground'
          )}
        >
          {status?.enabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>

      {status?.enabled ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Method</p>
              <p className="font-medium capitalize">{status.method || 'Authenticator App'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Backup Codes</p>
              <p className="font-medium">{status.backup_codes_remaining} remaining</p>
            </div>
          </div>

          {status.backup_codes_remaining <= 2 && (
            <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
              <div className="flex gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600 shrink-0 mt-0.5" />
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  You're running low on backup codes. Consider generating new ones.
                </p>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <Button variant="outline" size="sm" onClick={onRegenerateCodes}>
              <Key className="mr-2 h-4 w-4" />
              Regenerate Codes
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:text-destructive"
              onClick={onDisable}
            >
              Disable 2FA
            </Button>
          </div>
        </div>
      ) : (
        <Button onClick={onSetup}>
          <Shield className="mr-2 h-4 w-4" />
          Enable Two-Factor Authentication
        </Button>
      )}
    </div>
  );
}
