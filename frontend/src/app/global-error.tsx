'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Global application error:', error);
  }, [error]);

  return (
    <html>
      <body>
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
          <div className="text-center max-w-md">
            {/* Error Illustration */}
            <div className="mx-auto w-20 h-20 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-6">
              <AlertTriangle className="h-10 w-10 text-red-600 dark:text-red-400" aria-hidden="true" />
            </div>

            <h1 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">
              Critical Error
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              A critical error occurred. Please try refreshing the page.
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

            <button
              onClick={reset}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Try Again
            </button>

            <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
              If this problem persists, please contact{' '}
              <a
                href="mailto:support@nexusai.com"
                className="text-blue-600 hover:underline"
              >
                support@nexusai.com
              </a>
            </p>
          </div>
        </div>
      </body>
    </html>
  );
}
