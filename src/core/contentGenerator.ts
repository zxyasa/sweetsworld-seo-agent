import { Post, SocialContent } from '../types';
import { buildUtmUrl } from './utm';

function generateHashtags(platform: string): string {
  const hashtags = {
    facebook: ['#SweetsWorld', '#AussieSweets', '#SweetTreats', '#DessertLovers', '#AustralianSweets'],
    instagram: ['#SweetsWorld', '#AussieSweets', '#SweetTreats', '#DessertLovers', '#AustralianSweets', '#Foodie', '#Yum', '#Delicious', '#SweetTooth', '#AussieTreats', '#Confectionery', '#AustralianMade'],
    x: ['#SweetsWorld', '#AussieSweets', '#SweetTreats'],
    pinterest: [], // Pinterest uses keywords in description
    gbp: ['#SweetsWorld', '#AustralianSweets'],
    tiktok: ['#SweetsWorld', '#AussieSweets', '#SweetTreats', '#Candy', '#AustralianCandy', '#Confectionery'],
  };
  return hashtags[platform as keyof typeof hashtags].join(' ');
}

function generateVariantA(post: Post, platform: string, utmUrl: string): string {
  const hashtags = generateHashtags(platform);
  switch (platform) {
    case 'facebook':
      return `G'day! Check out our latest: "${post.title}"\n\n${post.excerpt}\n\nRead more: ${utmUrl}\n\n${hashtags}`;
    case 'instagram':
      return `🍬 New post! "${post.title}"\n\n${post.excerpt}\n\nLink in bio, mate! ${hashtags}`;
    case 'x':
      return `New: "${post.title}" - ${post.excerpt} ${utmUrl} ${hashtags}`;
    case 'pinterest':
      return `${post.title} - ${post.excerpt}`;
    case 'gbp':
      return `New: ${post.title} - ${post.excerpt}`;
    default:
      return '';
  }
}

function generateVariantB(post: Post, platform: string, utmUrl: string): string {
  const hashtags = generateHashtags(platform);
  switch (platform) {
    case 'facebook':
      return `🚨 Fresh from the kitchen! "${post.title}"\n\nHave a squiz at this ripper: ${post.excerpt}\n\n👉 ${utmUrl}\n\n${hashtags}`;
    case 'instagram':
      return `🔥 "${post.title}" is live! Aussie sweets await... 🍭\n\n${post.excerpt}\n\nTap the link, mate! ${hashtags}`;
    case 'x':
      return `Sweet news! "${post.title}" just dropped. ${post.excerpt} ${utmUrl} ${hashtags}`;
    case 'pinterest':
      return `Discover: ${post.title} - Perfect for sweet lovers! ${post.excerpt}`;
    case 'gbp':
      return `Exciting update: ${post.title} - ${post.excerpt}`;
    default:
      return '';
  }
}

export function generateSocialContent(post: Post): SocialContent {
  const utmUrl = buildUtmUrl(post.url, 'social', post.slug, 'a'); // Base UTM, variants will adjust
  const tiktokHashtags = generateHashtags('tiktok');

  // Generate TikTok caption (short and engaging)
  const tiktokCaption = `${post.title.substring(0, 100)} 🍬 ${tiktokHashtags}`;

  const platforms = {
    facebook: { message: generateVariantA(post, 'facebook', utmUrl) },
    instagram: { caption: generateVariantA(post, 'instagram', utmUrl) },
    x: { text: generateVariantA(post, 'x', utmUrl) },
    pinterest: { title: post.title, description: generateVariantA(post, 'pinterest', utmUrl), link: utmUrl },
    gbp: { summary: generateVariantA(post, 'gbp', utmUrl), cta: 'LEARN_MORE', link: utmUrl },
    tiktok: {
      title: post.title.substring(0, 150), // TikTok title limit
      caption: tiktokCaption,
      videoUrl: post.video, // Will be generated if not provided
    },
  };

  // For simplicity, using variant A. In full implementation, generate both and choose or return both.

  return {
    post,
    utm_url: utmUrl,
    platforms,
  };
}