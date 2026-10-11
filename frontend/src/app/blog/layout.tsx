import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { DoAideLogo } from '@/components/ui/doaide-logo';
import { DoAideFooter } from '@/components/ui/doaide-footer';

export const metadata: Metadata = {
  robots: 'index, follow',
};

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-lg"
      >
        Skip to main content
      </a>
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50" role="banner">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" aria-label="Back to GSTIndia homepage">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            <DoAideLogo size={20} />
            <span className="hidden sm:inline font-semibold text-foreground">DoAide</span>
            <span className="hidden sm:inline text-muted-foreground">|</span>
            <span className="font-medium text-foreground">GSTIndia</span>
          </Link>
          <nav className="flex items-center gap-3 sm:gap-6" aria-label="Blog navigation">
            <Link href="/blog" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Blog</Link>
            <Link href="/" className="text-sm font-medium text-primary-foreground bg-primary px-3 py-2 sm:px-4 rounded-lg hover:opacity-90 whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 transition-opacity">
              Try GST Tools Free
            </Link>
          </nav>
        </div>
      </header>
      <main id="main-content">{children}</main>
      <div className="mt-16">
        <DoAideFooter />
      </div>
    </div>
  );
}
