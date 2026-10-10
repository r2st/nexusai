import type { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://gst.doaide.com';

  return [
    {
      url: baseUrl,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/blog/gst-return-filing-guide-2026-27`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog/gst-registration-online-guide`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog/input-tax-credit-itc-rules-2026-27`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog/gst-invoice-format-guide`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog/gst-hsn-code-list`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog/gst-composition-scheme-guide`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: new Date('2026-10-10'),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ];
}
