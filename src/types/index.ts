export interface Post {
  title: string;
  url: string;
  slug: string;
  excerpt: string;
  image?: string;
  video?: string; // Optional video URL for TikTok
}

export interface SocialContent {
  post: Post;
  utm_url: string;
  platforms: {
    facebook: { message: string };
    instagram: { caption: string };
    x: { text: string };
    pinterest: { title: string; description: string; link: string };
    gbp: { summary: string; cta: string; link: string };
    tiktok: { title: string; caption: string; videoUrl?: string };
  };
}

export interface PublishLog {
  id?: number;
  timestamp: string;
  platform: string;
  variant: 'a' | 'b';
  post_url: string;
  utm_url: string;
  status: string;
  response_json?: string;
}

export type Platform = 'facebook' | 'instagram' | 'x' | 'pinterest' | 'gbp' | 'tiktok';