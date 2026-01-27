'use client';

/**
 * Secure Form Component
 * 
 * A form wrapper that includes built-in security features:
 * - CSRF token injection
 * - Input sanitization
 * - Rate limiting
 * - Honeypot field for bot detection
 */

import { FormEvent, ReactNode, useState, useRef, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { getCSRFToken, sanitizeInput, detectMaliciousPatterns, checkRateLimit } from '@/lib/security';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useRateLimit } from './rate-limit-feedback';

// =============================================================================
// TYPES
// =============================================================================

interface SecureFormProps {
  children: ReactNode;
  onSubmit: (data: FormData, csrfToken: string) => Promise<void>;
  className?: string;
  // Security options
  enableCSRF?: boolean;
  enableRateLimit?: boolean;
  rateLimitKey?: string;
  rateLimitMax?: number;
  rateLimitWindow?: number;
  enableHoneypot?: boolean;
  enableSanitization?: boolean;
  sanitizationOptions?: {
    allowBasicHtml?: boolean;
    maxLength?: number;
  };
  // UI options
  loadingText?: string;
  disabled?: boolean;
}

// =============================================================================
// SECURE FORM COMPONENT
// =============================================================================

export function SecureForm({
  children,
  onSubmit,
  className,
  enableCSRF = true,
  enableRateLimit = true,
  rateLimitKey = 'form_submit',
  rateLimitMax = 5,
  rateLimitWindow = 60000,
  enableHoneypot = true,
  enableSanitization = true,
  sanitizationOptions = {},
  loadingText = 'Submitting...',
  disabled = false,
}: SecureFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [csrfToken, setCsrfToken] = useState('');
  const honeypotRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const { setRateLimited } = useRateLimit();

  // Generate CSRF token on mount
  useEffect(() => {
    if (enableCSRF) {
      setCsrfToken(getCSRFToken());
    }
  }, [enableCSRF]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (isSubmitting || disabled) return;

    // Check honeypot - if filled, it's likely a bot
    if (enableHoneypot && honeypotRef.current?.value) {
      console.warn('Honeypot triggered - likely bot submission');
      // Fake success to not alert bots
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return;
    }

    // Check rate limit
    if (enableRateLimit) {
      const rateLimit = checkRateLimit(rateLimitKey, rateLimitMax, rateLimitWindow);
      if (!rateLimit.allowed) {
        setRateLimited(rateLimitKey, rateLimit.resetIn);
        toast.error(`Too many submissions. Please wait ${Math.ceil(rateLimit.resetIn / 1000)} seconds.`);
        return;
      }
    }

    // Get form data
    const formData = new FormData(e.currentTarget);

    // Sanitize inputs if enabled
    if (enableSanitization) {
      const sanitizedData = new FormData();
      
      for (const [key, value] of formData.entries()) {
        if (typeof value === 'string') {
          // Check for malicious patterns
          const detection = detectMaliciousPatterns(value);
          if (detection.isSuspicious) {
            console.warn(`Suspicious pattern detected in field "${key}":`, detection.patterns);
            toast.error('Invalid input detected. Please check your entries.');
            return;
          }
          
          // Sanitize the input
          const sanitized = sanitizeInput(value, sanitizationOptions);
          sanitizedData.append(key, sanitized);
        } else {
          // Files and other non-string values
          sanitizedData.append(key, value);
        }
      }
      
      // Replace formData with sanitized version
      formData.forEach((_, key) => formData.delete(key));
      sanitizedData.forEach((value, key) => formData.append(key, value));
    }

    // Remove honeypot field from submission
    formData.delete('_hp_field');

    setIsSubmitting(true);
    
    try {
      await onSubmit(formData, csrfToken);
    } catch (error) {
      console.error('Form submission error:', error);
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className={cn('relative', className)}
    >
      {/* CSRF Token */}
      {enableCSRF && (
        <input type="hidden" name="_csrf" value={csrfToken} />
      )}

      {/* Honeypot field - hidden from real users, but bots will fill it */}
      {enableHoneypot && (
        <div
          style={{
            position: 'absolute',
            left: '-9999px',
            top: '-9999px',
            opacity: 0,
            pointerEvents: 'none',
          }}
          aria-hidden="true"
          tabIndex={-1}
        >
          <label htmlFor="_hp_field">Leave this field empty</label>
          <input
            ref={honeypotRef}
            type="text"
            id="_hp_field"
            name="_hp_field"
            autoComplete="off"
            tabIndex={-1}
          />
        </div>
      )}

      {/* Form content */}
      {children}

      {/* Loading overlay */}
      {isSubmitting && (
        <div className="absolute inset-0 bg-background/50 flex items-center justify-center rounded-lg">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            {loadingText}
          </div>
        </div>
      )}
    </form>
  );
}

// =============================================================================
// SECURE INPUT WRAPPER
// =============================================================================

interface SecureInputProps {
  children: ReactNode;
  name: string;
  sanitize?: boolean;
  maxLength?: number;
  pattern?: RegExp;
  errorMessage?: string;
}

export function SecureInput({
  children,
  name,
  sanitize = true,
  maxLength = 1000,
  pattern,
  errorMessage = 'Invalid input',
}: SecureInputProps) {
  const [error, setError] = useState<string | null>(null);

  const validate = (value: string) => {
    // Length check
    if (value.length > maxLength) {
      setError(`Maximum ${maxLength} characters allowed`);
      return false;
    }

    // Pattern check
    if (pattern && !pattern.test(value)) {
      setError(errorMessage);
      return false;
    }

    // Malicious pattern check
    if (sanitize) {
      const detection = detectMaliciousPatterns(value);
      if (detection.isSuspicious) {
        setError('Invalid characters detected');
        return false;
      }
    }

    setError(null);
    return true;
  };

  return (
    <div className="space-y-1">
      {children}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}

// =============================================================================
// FORM SUBMISSION BUTTON
// =============================================================================

interface SecureSubmitButtonProps {
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}

export function SecureSubmitButton({
  children,
  className,
  disabled,
}: SecureSubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center rounded-md text-sm font-medium',
        'ring-offset-background transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'disabled:pointer-events-none disabled:opacity-50',
        'bg-primary text-primary-foreground hover:bg-primary/90',
        'h-10 px-4 py-2',
        className
      )}
    >
      {children}
    </button>
  );
}
