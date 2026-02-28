export function buildUtmUrl(baseUrl: string, platform: string, slug: string, variant: 'a' | 'b'): string {
  const url = new URL(baseUrl);
  url.searchParams.set('utm_source', platform);
  url.searchParams.set('utm_medium', 'social');
  url.searchParams.set('utm_campaign', slug);
  url.searchParams.set('utm_content', variant);
  return url.toString();
}