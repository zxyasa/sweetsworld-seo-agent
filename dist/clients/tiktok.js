"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.postToTikTok = postToTikTok;
exports.postVideoToTikTok = postVideoToTikTok;
const config_1 = require("../config");
async function postToTikTok(options) {
    const { accessToken } = config_1.config.tiktok;
    if (!accessToken) {
        return {
            status: 'NOT_CONFIGURED',
            response: { error: 'TikTok credentials not configured. Need access token with video.publish scope' }
        };
    }
    const { videoUrl, title, caption = '', privacyLevel = 'PUBLIC_TO_EVERYONE', disableComment = false, disableDuet = false, disableStitch = false, } = options;
    try {
        console.log('📱 Posting video to TikTok...');
        // Step 1: Initialize video upload
        const initResponse = await fetch('https://open.tiktokapis.com/v2/post/publish/video/init/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json; charset=UTF-8',
            },
            body: JSON.stringify({
                post_info: {
                    title: title,
                    description: caption,
                    privacy_level: privacyLevel,
                    disable_comment: disableComment,
                    disable_duet: disableDuet,
                    disable_stitch: disableStitch,
                    video_cover_timestamp_ms: 0,
                },
                source_info: {
                    source: 'FILE_URL',
                    video_url: videoUrl,
                },
            }),
        });
        if (!initResponse.ok) {
            const errorData = await initResponse.json();
            console.error('TikTok Init Error:', errorData);
            return {
                status: 'ERROR',
                response: {
                    error: errorData.error?.message || 'Failed to initialize TikTok upload',
                    code: errorData.error?.code,
                }
            };
        }
        const initData = await initResponse.json();
        const publishId = initData.data?.publish_id;
        if (!publishId) {
            console.error('TikTok Init Response:', initData);
            return {
                status: 'ERROR',
                response: { error: 'No publish_id returned from TikTok' }
            };
        }
        console.log(`🎬 TikTok upload initialized: ${publishId}`);
        // Step 2: Check upload status (polling)
        const maxAttempts = 60; // 2 minutes max
        let attempts = 0;
        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
            const statusResponse = await fetch(`https://open.tiktokapis.com/v2/post/publish/status/fetch/?publish_id=${publishId}`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                },
            });
            if (!statusResponse.ok) {
                const errorData = await statusResponse.json();
                console.error('TikTok Status Error:', errorData);
                continue; // Try again
            }
            const statusData = await statusResponse.json();
            const status = statusData.data?.status;
            if (status === 'PUBLISH_COMPLETE') {
                console.log('✅ TikTok video published successfully!');
                return {
                    status: 'SUCCESS',
                    response: {
                        publish_id: publishId,
                        ...statusData.data
                    }
                };
            }
            else if (status === 'FAILED') {
                console.error('TikTok Upload Failed:', statusData);
                return {
                    status: 'ERROR',
                    response: {
                        error: statusData.data?.fail_reason || 'Upload failed',
                        publish_id: publishId
                    }
                };
            }
            attempts++;
            console.log(`⏳ TikTok upload in progress... (${attempts}/${maxAttempts}) - Status: ${status}`);
        }
        return {
            status: 'TIMEOUT',
            response: {
                error: 'TikTok upload timed out after 2 minutes',
                publish_id: publishId
            }
        };
    }
    catch (error) {
        console.error('TikTok API Exception:', error);
        return {
            status: 'ERROR',
            response: { error: error.message }
        };
    }
}
/**
 * Post a video to TikTok with simple parameters
 */
async function postVideoToTikTok(videoUrl, title, caption) {
    return postToTikTok({
        videoUrl,
        title,
        caption,
        privacyLevel: 'PUBLIC_TO_EVERYONE',
        disableComment: false,
        disableDuet: true,
        disableStitch: true,
    });
}
