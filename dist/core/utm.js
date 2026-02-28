"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildUtmUrl = buildUtmUrl;
function buildUtmUrl(baseUrl, platform, slug, variant) {
    const url = new URL(baseUrl);
    url.searchParams.set('utm_source', platform);
    url.searchParams.set('utm_medium', 'social');
    url.searchParams.set('utm_campaign', slug);
    url.searchParams.set('utm_content', variant);
    return url.toString();
}
