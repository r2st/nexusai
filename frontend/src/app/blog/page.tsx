import type { Metadata } from 'next';
import Link from 'next/link';
import { Calendar, Clock, ArrowRight } from 'lucide-react';

export const metadata: Metadata = {
  title: 'GST Blog - Latest GST News, Guides & Updates | GSTIndia',
  description: 'Expert guides on GST return filing, registration, Input Tax Credit rules, HSN codes, and more. Stay updated with the latest GST news and compliance tips.',
  openGraph: {
    title: 'GST Blog - Latest GST News, Guides & Updates | GSTIndia',
    description: 'Expert guides on GST return filing, registration, Input Tax Credit rules, and more.',
    url: 'https://gst.doaide.com/blog',
    type: 'website',
  },
};

const blogPosts = [
  {
    slug: 'gst-invoice-format-guide',
    title: 'GST Invoice Format 2026: Mandatory Fields, Templates & E-Invoicing Rules',
    description: 'Complete guide to GST invoice format with mandatory fields, templates, e-invoicing rules, and bill of supply format for Indian businesses in 2026-27.',
    date: '2026-10-10',
    readTime: '16 min read',
    category: 'Invoicing',
  },
  {
    slug: 'gst-hsn-code-list',
    title: 'GST HSN Code List 2026: Complete Guide to Finding HSN & SAC Codes',
    description: 'Complete HSN code list for GST with chapter-wise breakdown. Find HSN codes for goods and SAC codes for services. Updated for 2026-27 with search guide.',
    date: '2026-10-10',
    readTime: '18 min read',
    category: 'HSN Codes',
  },
  {
    slug: 'gst-composition-scheme-guide',
    title: 'GST Composition Scheme 2026: Eligibility, Tax Rates & Filing Guide',
    description: 'Complete guide to GST Composition Scheme — eligibility, tax rates, GSTR-4 filing, benefits vs regular scheme. Updated for 2026-27 with practical examples.',
    date: '2026-10-10',
    readTime: '15 min read',
    category: 'Composition Scheme',
  },
  {
    slug: 'gst-return-filing-guide-2026-27',
    title: 'GST Return Filing Guide 2026-27: Step-by-Step Process, Due Dates & Penalties',
    description: 'Complete guide to filing GST returns in 2026-27. Learn step-by-step GSTR-1, GSTR-3B filing process, due dates, late fees, and how to avoid penalties.',
    date: '2026-10-10',
    readTime: '15 min read',
    category: 'GST Filing',
  },
  {
    slug: 'gst-registration-online-guide',
    title: 'GST Registration Online: Complete Guide to Getting Your GST Number in 2026',
    description: 'Step-by-step guide to GST registration online. Documents required, eligibility criteria, and how to get your GSTIN on the GST portal in 2026.',
    date: '2026-10-10',
    readTime: '12 min read',
    category: 'Registration',
  },
  {
    slug: 'input-tax-credit-itc-rules-2026-27',
    title: 'Input Tax Credit (ITC) Rules 2026-27: Complete Guide to Claiming ITC Under GST',
    description: 'Everything about Input Tax Credit under GST — eligibility, conditions, reversal rules, time limits, and common mistakes to avoid when claiming ITC.',
    date: '2026-10-10',
    readTime: '14 min read',
    category: 'ITC & Credits',
  },
];

export default function BlogIndex() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">GST Blog</h1>
      <p className="text-lg text-gray-600 mb-12">Expert guides, latest updates, and practical tips for GST compliance in India.</p>

      <div className="space-y-8">
        {blogPosts.map((post) => (
          <article key={post.slug} className="border rounded-xl p-6 hover:shadow-lg transition-shadow bg-white">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">{post.category}</span>
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Calendar className="h-3 w-3" />
                {new Date(post.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
              </span>
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Clock className="h-3 w-3" />
                {post.readTime}
              </span>
            </div>
            <Link href={`/blog/${post.slug}`}>
              <h2 className="text-xl font-bold text-gray-900 mb-2 hover:text-blue-600 transition-colors">{post.title}</h2>
            </Link>
            <p className="text-gray-600 mb-4">{post.description}</p>
            <Link href={`/blog/${post.slug}`} className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700">
              Read full guide <ArrowRight className="h-4 w-4" />
            </Link>
          </article>
        ))}
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Blog',
            name: 'GSTIndia Blog',
            description: 'Expert guides on GST compliance, return filing, registration, and tax credits for Indian businesses.',
            url: 'https://gst.doaide.com/blog',
            publisher: {
              '@type': 'Organization',
              name: 'DoAide Technologies',
              url: 'https://gst.doaide.com',
            },
          }),
        }}
      />
    </div>
  );
}
