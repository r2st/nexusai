'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <div className="text-center max-w-md">
        {/* Error Illustration */}
        <div className="mx-auto w-20 h-20 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-6">
          <AlertTriangle className="h-10 w-10 text-red-600 dark:text-red-400" aria-hidden="true" />
        </div>

        <h1 className="text-3xl font-bold mb-2">Something went wrong</h1>
        <p className="text-muted-foreground mb-6">
          We encountered an unexpected error. Our team has been notified and is working on a fix.
        </p>

        {/* Error Details (only in development) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-left">
            <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
              Error Details:
            </p>
            <p className="text-xs font-mono text-red-700 dark:text-red-300 break-all">
              {error.message}
            </p>
            {error.digest && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                Error ID: {error.digest}
              </p>
            )}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={reset}>
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            Try Again
          </Button>
          <Link href="/">
            <Button variant="outline">
              <Home className="mr-2 h-4 w-4" aria-hidden="true" />
              Go Home
            </Button>
          </Link>
        </div>

        {/* Report Bug */}
        <div className="mt-8 pt-6 border-t">
          <p className="text-sm text-muted-foreground mb-3">
            If this problem persists, please let us know:
          </p>
          <a
            href="mailto:support@nexusai.com?subject=Bug%20Report"
            className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
          >
            <Bug className="h-4 w-4" aria-hidden="true" />
            Report this issue
          </a>
        </div>
      </div>
    </div>
  );
}
