"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerRoutes = registerRoutes;
const contentGenerator_1 = require("../core/contentGenerator");
const validate_1 = require("../core/validate");
const sqlite_1 = require("../db/sqlite");
const config_1 = require("../config");
const facebook_1 = require("../clients/facebook");
const instagram_1 = require("../clients/instagram");
const x_1 = require("../clients/x");
const pinterest_1 = require("../clients/pinterest");
const gbp_1 = require("../clients/gbp");
const tiktok_1 = require("../clients/tiktok");
const did_1 = require("../clients/did");
async function publishToPlatform(platform, content, post, variant) {
    const utmUrl = content.utm_url; // Adjust for variant if needed
    let result;
    switch (platform) {
        case 'facebook':
            result = await (0, facebook_1.postToFacebook)(content.platforms.facebook.message);
            break;
        case 'instagram':
            result = await (0, instagram_1.postToInstagram)(content.platforms.instagram.caption, post.image);
            break;
        case 'x':
            result = await (0, x_1.postToX)(content.platforms.x.text);
            break;
        case 'pinterest':
            result = await (0, pinterest_1.postToPinterest)(content.platforms.pinterest.title, content.platforms.pinterest.description, content.platforms.pinterest.link, post.image);
            break;
        case 'gbp':
            result = await (0, gbp_1.postToGBP)(content.platforms.gbp.summary, content.platforms.gbp.cta, content.platforms.gbp.link);
            break;
        case 'tiktok':
            // TikTok requires a video - generate if not provided
            let videoUrl = content.platforms.tiktok.videoUrl;
            if (!videoUrl && config_1.config.did.apiKey) {
                console.log('🎬 Generating video for TikTok using D-ID...');
                const videoResult = await (0, did_1.generateSocialVideo)(post.title, post.excerpt);
                if (videoResult.status === 'SUCCESS' && videoResult.videoUrl) {
                    videoUrl = videoResult.videoUrl;
                    console.log('✅ Video generated:', videoUrl);
                }
                else {
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
            }
            else {
                result = await (0, tiktok_1.postVideoToTikTok)(videoUrl, content.platforms.tiktok.title, content.platforms.tiktok.caption);
            }
            break;
    }
    (0, sqlite_1.logPublishAttempt)({
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
async function registerRoutes(fastify) {
    fastify.get('/health', async () => {
        return { status: 'ok' };
    });
    fastify.post('/webhook/wp', async (request, reply) => {
        const validation = (0, validate_1.validateInput)(request.body);
        if (!validation.success) {
            return reply.code(400).send({ error: 'Invalid input', details: validation.error });
        }
        const post = validation.data;
        const content = (0, contentGenerator_1.generateSocialContent)(post);
        if (config_1.config.publishMode === 'live') {
            // Publish to all platforms
            const platforms = ['facebook', 'instagram', 'x', 'pinterest', 'gbp', 'tiktok'];
            for (const platform of platforms) {
                await publishToPlatform(platform, content, post, 'a'); // For now, only variant a
            }
        }
        return content;
    });
}
