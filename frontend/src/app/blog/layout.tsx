import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata: Metadata = {
  robots: 'index, follow',
};

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded-lg"
      >
        Skip to main content
      </a>
      <header className="border-b bg-white dark:bg-gray-950 dark:border-gray-800 sticky top-0 z-50" role="banner">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100" aria-label="Back to GSTIndia homepage">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">GSTIndia by DoAide</span>
            <span className="sm:hidden">GSTIndia</span>
          </Link>
          <nav className="flex items-center gap-3 sm:gap-6" aria-label="Blog navigation">
            <Link href="/blog" className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">Blog</Link>
            <Link href="/" className="text-sm font-medium text-white bg-blue-600 px-3 py-2 sm:px-4 rounded-lg hover:bg-blue-700 whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
              Try GST Tools Free
            </Link>
          </nav>
        </div>
      </header>
      <main id="main-content">{children}</main>
      <footer className="border-t bg-gray-50 dark:bg-gray-900 dark:border-gray-800 py-12 mt-16" role="contentinfo">
        <div className="container mx-auto px-4">
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-8">
            <div>
              <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">GSTIndia by DoAide</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">AI-powered GST compliance tools for Indian businesses. Simplify your GST return filing, registration, and ITC claims.</p>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">GST Tools</h3>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400">GST Calculator</Link></li>
                <li><Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400">HSN Code Finder</Link></li>
                <li><Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400">GSTIN Validator</Link></li>
                <li><Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400">GST Return Filing</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">Resources</h3>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><Link href="/blog/gst-return-filing-guide-2026-27" className="hover:text-blue-600 dark:hover:text-blue-400">GST Return Filing Guide</Link></li>
                <li><Link href="/blog/gst-registration-online-guide" className="hover:text-blue-600 dark:hover:text-blue-400">GST Registration Guide</Link></li>
                <li><Link href="/blog/input-tax-credit-itc-rules-2026-27" className="hover:text-blue-600 dark:hover:text-blue-400">ITC Rules Guide</Link></li>
                <li><Link href="/blog/gst-invoice-format-guide" className="hover:text-blue-600 dark:hover:text-blue-400">GST Invoice Format</Link></li>
                <li><Link href="/blog/gst-hsn-code-list" className="hover:text-blue-600 dark:hover:text-blue-400">HSN Code List</Link></li>
                <li><Link href="/blog/gst-composition-scheme-guide" className="hover:text-blue-600 dark:hover:text-blue-400">Composition Scheme Guide</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t dark:border-gray-800 text-center text-sm text-gray-500 dark:text-gray-400">
            © 2026 DoAide Technologies. All rights reserved. | <Link href="/privacy" className="hover:text-blue-600 dark:hover:text-blue-400">Privacy Policy</Link> | <Link href="/terms" className="hover:text-blue-600 dark:hover:text-blue-400">Terms of Service</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
