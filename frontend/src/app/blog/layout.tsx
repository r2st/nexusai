import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata: Metadata = {
  robots: 'index, follow',
};

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b bg-white sticky top-0 z-50">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-4 w-4" />
            GSTIndia by DoAide
          </Link>
          <nav className="flex items-center gap-6">
            <Link href="/blog" className="text-sm font-medium text-gray-600 hover:text-gray-900">Blog</Link>
            <Link href="/" className="text-sm font-medium text-white bg-blue-600 px-4 py-2 rounded-lg hover:bg-blue-700">
              Try GST Tools Free
            </Link>
          </nav>
        </div>
      </header>
      <main>{children}</main>
      <footer className="border-t bg-gray-50 py-12 mt-16">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <h3 className="font-bold text-gray-900 mb-3">GSTIndia by DoAide</h3>
              <p className="text-sm text-gray-600">AI-powered GST compliance tools for Indian businesses. Simplify your GST return filing, registration, and ITC claims.</p>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 mb-3">GST Tools</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><Link href="/" className="hover:text-blue-600">GST Calculator</Link></li>
                <li><Link href="/" className="hover:text-blue-600">HSN Code Finder</Link></li>
                <li><Link href="/" className="hover:text-blue-600">GSTIN Validator</Link></li>
                <li><Link href="/" className="hover:text-blue-600">GST Return Filing</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 mb-3">Resources</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><Link href="/blog/gst-return-filing-guide-2026-27" className="hover:text-blue-600">GST Return Filing Guide</Link></li>
                <li><Link href="/blog/gst-registration-online-guide" className="hover:text-blue-600">GST Registration Guide</Link></li>
                <li><Link href="/blog/input-tax-credit-itc-rules-2026-27" className="hover:text-blue-600">ITC Rules Guide</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t text-center text-sm text-gray-500">
            © 2026 DoAide Technologies. All rights reserved. | <Link href="/privacy" className="hover:text-blue-600">Privacy Policy</Link> | <Link href="/terms" className="hover:text-blue-600">Terms of Service</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
