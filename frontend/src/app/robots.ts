import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/admin/', '/api/', '/settings/', '/chat/', '/setup/'],
    },
    sitemap: 'https://gst.doaide.com/sitemap.xml',
  };
}
