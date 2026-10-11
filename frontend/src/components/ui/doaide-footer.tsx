'use client';

import Link from 'next/link';
import { DoAideLogo } from '@/components/ui/doaide-logo';

const doaideProducts = [
  { name: 'GSTIndia', href: 'https://gst.doaide.com', description: 'GST Compliance' },
  { name: 'TaxFile', href: 'https://tax.doaide.com', description: 'Income Tax Filing' },
  { name: 'SalaryDecode', href: 'https://salary.doaide.com', description: 'Salary Calculator' },
  { name: 'Invoicer', href: 'https://invoicer.doaide.com', description: 'Invoice Generator' },
  { name: 'Resume', href: 'https://resume.doaide.com', description: 'Resume Builder' },
  { name: 'InsureKit', href: 'https://insure.doaide.com', description: 'Insurance Tools' },
  { name: 'Prospect', href: 'https://prospect.doaide.com', description: 'Sales CRM' },
  { name: 'Cortex', href: 'https://cortex.doaide.com', description: 'Knowledge Management' },
];

interface DoAideFooterProps {
  productName?: string;
}

export function DoAideFooter({ productName = 'GSTIndia' }: DoAideFooterProps) {
  return (
    <footer className="border-t bg-muted/30 dark:bg-background">
      <div className="container mx-auto px-4 py-12">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <DoAideLogo size={22} />
              <span className="font-bold text-foreground">DoAide</span>
              <span className="text-muted-foreground">|</span>
              <span className="font-medium text-foreground">{productName}</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              AI-powered GST compliance tools for Indian businesses. Simplify your GST return filing, registration, and ITC claims.
            </p>
            <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-xs font-medium">
              <DoAideLogo size={14} />
              A DoAide Product
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-3 text-sm">GST Tools</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link href="/" className="hover:text-primary transition-colors">GST Calculator</Link></li>
              <li><Link href="/" className="hover:text-primary transition-colors">HSN Code Finder</Link></li>
              <li><Link href="/" className="hover:text-primary transition-colors">GSTIN Validator</Link></li>
              <li><Link href="/" className="hover:text-primary transition-colors">GST Return Filing</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-3 text-sm">Resources</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link href="/blog" className="hover:text-primary transition-colors">Blog</Link></li>
              <li><Link href="/blog/gst-return-filing-guide-2026-27" className="hover:text-primary transition-colors">GST Filing Guide</Link></li>
              <li><Link href="/blog/gst-registration-online-guide" className="hover:text-primary transition-colors">Registration Guide</Link></li>
              <li><Link href="/blog/input-tax-credit-itc-rules-2026-27" className="hover:text-primary transition-colors">ITC Rules</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-3 text-sm">More from DoAide</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {doaideProducts
                .filter((p) => p.name !== productName)
                .slice(0, 6)
                .map((product) => (
                  <li key={product.name}>
                    <a
                      href={product.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-primary transition-colors"
                    >
                      {product.name}
                      <span className="text-muted-foreground/60 ml-1">— {product.description}</span>
                    </a>
                  </li>
                ))}
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <span>&copy; {new Date().getFullYear()} DoAide Technologies. All rights reserved.</span>
          <nav className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-foreground transition-colors">Terms</Link>
            <a href="https://doaide.com" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">doaide.com</a>
          </nav>
        </div>
      </div>
    </footer>
  );
}
