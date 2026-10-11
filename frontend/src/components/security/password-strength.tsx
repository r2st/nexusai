'use client';

/**
 * Password Strength Components
 * 
 * Provides real-time password strength analysis and requirements checking.
 */

import { useMemo, useState } from 'react';
import { Check, X, Eye, EyeOff, AlertTriangle, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// TYPES
// =============================================================================

interface PasswordRequirement {
  id: string;
  label: string;
  test: (password: string) => boolean;
}

interface PasswordStrengthResult {
  score: number; // 0-4
  level: 'weak' | 'fair' | 'good' | 'strong' | 'very_strong';
  label: string;
  color: string;
  suggestions: string[];
}

// =============================================================================
// PASSWORD REQUIREMENTS
// =============================================================================

export const DEFAULT_REQUIREMENTS: PasswordRequirement[] = [
  {
    id: 'length',
    label: 'At least 8 characters',
    test: (pw) => pw.length >= 8,
  },
  {
    id: 'uppercase',
    label: 'One uppercase letter',
    test: (pw) => /[A-Z]/.test(pw),
  },
  {
    id: 'lowercase',
    label: 'One lowercase letter',
    test: (pw) => /[a-z]/.test(pw),
  },
  {
    id: 'number',
    label: 'One number',
    test: (pw) => /\d/.test(pw),
  },
  {
    id: 'special',
    label: 'One special character (!@#$%^&*)',
    test: (pw) => /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw),
  },
];

export const STRICT_REQUIREMENTS: PasswordRequirement[] = [
  ...DEFAULT_REQUIREMENTS,
  {
    id: 'length12',
    label: 'At least 12 characters',
    test: (pw) => pw.length >= 12,
  },
  {
    id: 'no_common',
    label: 'Not a common password',
    test: (pw) => !COMMON_PASSWORDS.includes(pw.toLowerCase()),
  },
];

// Common passwords to check against
const COMMON_PASSWORDS = [
  'password', '123456', '12345678', 'qwerty', 'abc123', 'monkey', '1234567',
  'letmein', 'trustno1', 'dragon', 'baseball', 'iloveyou', 'master', 'sunshine',
  'ashley', 'bailey', 'passw0rd', 'shadow', '123123', '654321', 'superman',
  'qazwsx', 'michael', 'football', 'password1', 'password123', 'welcome',
];

// =============================================================================
// PASSWORD STRENGTH CALCULATOR
// =============================================================================

export function calculatePasswordStrength(password: string): PasswordStrengthResult {
  if (!password) {
    return {
      score: 0,
      level: 'weak',
      label: 'Enter a password',
      color: 'bg-muted',
      suggestions: ['Start typing to see password strength'],
    };
  }

  let score = 0;
  const suggestions: string[] = [];

  // Length scoring
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (password.length >= 16) score += 1;
  if (password.length < 8) suggestions.push('Use at least 8 characters');

  // Character variety scoring
  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password);

  if (hasLower) score += 0.5;
  if (hasUpper) score += 0.5;
  if (hasNumber) score += 0.5;
  if (hasSpecial) score += 1;

  if (!hasUpper) suggestions.push('Add uppercase letters');
  if (!hasLower) suggestions.push('Add lowercase letters');
  if (!hasNumber) suggestions.push('Add numbers');
  if (!hasSpecial) suggestions.push('Add special characters');

  // Penalize common patterns
  if (/^[a-z]+$/i.test(password)) {
    score -= 1;
    suggestions.push('Avoid using only letters');
  }
  if (/^\d+$/.test(password)) {
    score -= 1;
    suggestions.push('Avoid using only numbers');
  }
  if (/(.)\1{2,}/.test(password)) {
    score -= 0.5;
    suggestions.push('Avoid repeated characters');
  }
  if (COMMON_PASSWORDS.includes(password.toLowerCase())) {
    score = 0;
    suggestions.unshift('This is a commonly used password');
  }

  // Sequential characters penalty
  if (/(?:abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz|012|123|234|345|456|567|678|789)/i.test(password)) {
    score -= 0.5;
    suggestions.push('Avoid sequential characters');
  }

  // Keyboard patterns penalty
  if (/(?:qwerty|asdf|zxcv|qazwsx)/i.test(password)) {
    score -= 1;
    suggestions.push('Avoid keyboard patterns');
  }

  // Normalize score
  score = Math.max(0, Math.min(4, Math.round(score)));

  const levels: Record<number, Omit<PasswordStrengthResult, 'score' | 'suggestions'>> = {
    0: { level: 'weak', label: 'Weak', color: 'bg-red-500' },
    1: { level: 'fair', label: 'Fair', color: 'bg-orange-500' },
    2: { level: 'good', label: 'Good', color: 'bg-yellow-500' },
    3: { level: 'strong', label: 'Strong', color: 'bg-green-500' },
    4: { level: 'very_strong', label: 'Very Strong', color: 'bg-green-600' },
  };

  return {
    score,
    ...levels[score],
    suggestions: suggestions.slice(0, 3),
  };
}

// =============================================================================
// PASSWORD STRENGTH METER
// =============================================================================

interface PasswordStrengthMeterProps {
  password: string;
  className?: string;
  showLabel?: boolean;
  showSuggestions?: boolean;
}

export function PasswordStrengthMeter({
  password,
  className,
  showLabel = true,
  showSuggestions = false,
}: PasswordStrengthMeterProps) {
  const strength = useMemo(() => calculatePasswordStrength(password), [password]);

  return (
    <div className={cn('space-y-2', className)}>
      {/* Strength bar */}
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map((index) => (
          <div
            key={index}
            className={cn(
              'h-1.5 flex-1 rounded-full transition-colors',
              index <= strength.score && password ? strength.color : 'bg-muted'
            )}
          />
        ))}
      </div>

      {/* Label */}
      {showLabel && password && (
        <div className="flex items-center justify-between">
          <span
            className={cn(
              'text-xs font-medium',
              strength.score <= 1 && 'text-red-500',
              strength.score === 2 && 'text-yellow-500',
              strength.score >= 3 && 'text-green-500'
            )}
          >
            {strength.label}
          </span>
        </div>
      )}

      {/* Suggestions */}
      {showSuggestions && strength.suggestions.length > 0 && (
        <ul className="text-xs text-muted-foreground space-y-1">
          {strength.suggestions.map((suggestion, index) => (
            <li key={index} className="flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-yellow-500" />
              {suggestion}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// =============================================================================
// PASSWORD REQUIREMENTS CHECKLIST
// =============================================================================

interface PasswordRequirementsProps {
  password: string;
  requirements?: PasswordRequirement[];
  className?: string;
}

export function PasswordRequirements({
  password,
  requirements = DEFAULT_REQUIREMENTS,
  className,
}: PasswordRequirementsProps) {
  const results = useMemo(
    () =>
      requirements.map((req) => ({
        ...req,
        met: req.test(password),
      })),
    [password, requirements]
  );

  const allMet = results.every((r) => r.met);

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center gap-2">
        <Shield
          className={cn(
            'h-4 w-4',
            allMet ? 'text-green-500' : 'text-muted-foreground'
          )}
        />
        <span className="text-sm font-medium">Password Requirements</span>
      </div>
      <ul className="space-y-1">
        {results.map((req) => (
          <li
            key={req.id}
            className={cn(
              'flex items-center gap-2 text-sm transition-colors',
              req.met ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'
            )}
          >
            {req.met ? (
              <Check className="h-4 w-4" />
            ) : (
              <X className="h-4 w-4" />
            )}
            {req.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

// =============================================================================
// PASSWORD INPUT WITH STRENGTH
// =============================================================================

interface PasswordInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  showStrength?: boolean;
  showRequirements?: boolean;
  requirements?: PasswordRequirement[];
  className?: string;
  disabled?: boolean;
  autoComplete?: string;
  name?: string;
  id?: string;
}

export function PasswordInput({
  value,
  onChange,
  placeholder = 'Enter password',
  showStrength = true,
  showRequirements = false,
  requirements = DEFAULT_REQUIREMENTS,
  className,
  disabled = false,
  autoComplete = 'new-password',
  name = 'password',
  id,
}: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className={cn('space-y-3', className)}>
      <div className="relative">
        <input
          type={showPassword ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={autoComplete}
          name={name}
          id={id}
          className={cn(
            'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm',
            'ring-offset-background placeholder:text-muted-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'pr-10'
          )}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          tabIndex={-1}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Eye className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>

      {showStrength && value && (
        <PasswordStrengthMeter password={value} showSuggestions />
      )}

      {showRequirements && (
        <PasswordRequirements password={value} requirements={requirements} />
      )}
    </div>
  );
}

// =============================================================================
// PASSWORD CONFIRMATION
// =============================================================================

interface PasswordConfirmationProps {
  password: string;
  confirmPassword: string;
  onPasswordChange: (value: string) => void;
  onConfirmChange: (value: string) => void;
  showStrength?: boolean;
  showRequirements?: boolean;
  requirements?: PasswordRequirement[];
  className?: string;
}

export function PasswordConfirmation({
  password,
  confirmPassword,
  onPasswordChange,
  onConfirmChange,
  showStrength = true,
  showRequirements = true,
  requirements = DEFAULT_REQUIREMENTS,
  className,
}: PasswordConfirmationProps) {
  const passwordsMatch = password && confirmPassword && password === confirmPassword;
  const showMismatch = confirmPassword && password !== confirmPassword;

  return (
    <div className={cn('space-y-4', className)}>
      <div>
        <label className="text-sm font-medium mb-1.5 block">Password</label>
        <PasswordInput
          value={password}
          onChange={onPasswordChange}
          showStrength={showStrength}
          showRequirements={showRequirements}
          requirements={requirements}
          placeholder="Create a password"
        />
      </div>

      <div>
        <label className="text-sm font-medium mb-1.5 block">Confirm Password</label>
        <div className="relative">
          <PasswordInput
            value={confirmPassword}
            onChange={onConfirmChange}
            showStrength={false}
            showRequirements={false}
            placeholder="Confirm your password"
          />
        </div>
        {showMismatch && (
          <p className="text-sm text-destructive mt-1.5 flex items-center gap-1">
            <X className="h-4 w-4" />
            Passwords do not match
          </p>
        )}
        {passwordsMatch && (
          <p className="text-sm text-green-600 mt-1.5 flex items-center gap-1">
            <Check className="h-4 w-4" />
            Passwords match
          </p>
        )}
      </div>
    </div>
  );
}

