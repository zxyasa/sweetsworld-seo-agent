import { FastifyInstance } from 'fastify';
import { generateSocialContent } from '../core/contentGenerator';
import { validateInput } from '../core/validate';
import { logPublishAttempt } from '../db/sqlite';
import { config } from '../config';
import { Post, Platform } from '../types';
import { postToFacebook } from '../clients/facebook';
import { postToInstagram } from '../clients/instagram';
import { postToX } from '../clients/x';
import { postToPinterest } from '../clients/pinterest';
import { postToGBP } from '../clients/gbp';
import { postVideoToTikTok } from '../clients/tiktok';
import { generateSocialVideo } from '../clients/did';

async function publishToPlatform(platform: Platform, content: any, post: Post, variant: 'a' | 'b') {
  const utmUrl = content.utm_url; // Adjust for variant if needed
  let result;
  switch (platform) {
    case 'facebook':
      result = await postToFacebook(content.platforms.facebook.message);
      break;
    case 'instagram':
      result = await postToInstagram(content.platforms.instagram.caption, post.image);
      break;
    case 'x':
      result = await postToX(content.platforms.x.text);
      break;
    case 'pinterest':
      result = await postToPinterest(content.platforms.pinterest.title, content.platforms.pinterest.description, content.platforms.pinterest.link, post.image);
      break;
    case 'gbp':
      result = await postToGBP(content.platforms.gbp.summary, content.platforms.gbp.cta, content.platforms.gbp.link);
      break;
    case 'tiktok':
      // TikTok requires a video - generate if not provided
      let videoUrl = content.platforms.tiktok.videoUrl;

      if (!videoUrl && config.did.apiKey) {
        console.log('🎬 Generating video for TikTok using D-ID...');
        const videoResult = await generateSocialVideo(post.title, post.excerpt);

        if (videoResult.status === 'SUCCESS' && videoResult.videoUrl) {
          videoUrl = videoResult.videoUrl;
          console.log('✅ Video generated:', videoUrl);
        } else {
          console.error('❌ Video generation failed:', videoResult.error);
          result = {
            status: 'ERROR',
            response: { error: `Video generation failed: ${videoResult.error}` }
          };
          break;
        }
      }

      if (!videoUrl) {
        console.log('⚠️  TikTok post skipped: No video available and D-ID not configured');
        result = {
          status: 'SKIPPED',
          response: { error: 'TikTok requires video. Either provide video URL or configure D-ID API for auto-generation.' }
        };
      } else {
        result = await postVideoToTikTok(
          videoUrl,
          content.platforms.tiktok.title,
          content.platforms.tiktok.caption
        );
      }
      break;
  }
  logPublishAttempt({
    timestamp: new Date().toISOString(),
    platform,
    variant,
    post_url: post.url,
    utm_url: utmUrl,
    status: result.status,
    response_json: JSON.stringify(result.response),
  });
  return result;
}

export async function registerRoutes(fastify: FastifyInstance) {
  fastify.get('/health', async () => {
    return { status: 'ok' };
  });

  fastify.post('/webhook/wp', async (request, reply) => {
    const validation = validateInput(request.body);
    if (!validation.success) {
      return reply.code(400).send({ error: 'Invalid input', details: validation.error });
    }

    const post: Post = validation.data;
    const content = generateSocialContent(post);

    if (config.publishMode === 'live') {
      // Publish to all platforms
      const platforms: Platform[] = ['facebook', 'instagram', 'x', 'pinterest', 'gbp', 'tiktok'];
      for (const platform of platforms) {
        await publishToPlatform(platform, content, post, 'a'); // For now, only variant a
      }
    }

    return content;
  });
}