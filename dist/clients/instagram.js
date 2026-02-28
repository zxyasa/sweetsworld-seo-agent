"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.postToInstagram = postToInstagram;
const config_1 = require("../config");
async function postToInstagram(caption, imageUrl) {
    if (!config_1.config.instagram.businessId || !config_1.config.facebook.accessToken) {
        return { status: 'NOT_CONFIGURED', response: { error: 'Instagram credentials not configured' } };
    }
    // Instagram requires an image - cannot post text-only
    if (!imageUrl) {
        console.log('⚠️  Instagram post skipped: No image provided (Instagram requires images)');
        return { status: 'SKIPPED', response: { error: 'Instagram requires an image URL' } };
    }
    try {
        // Step 1: Create media container
        const containerResponse = await fetch(`https://graph.facebook.com/v18.0/${config_1.config.instagram.businessId}/media`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_url: imageUrl,
                caption: caption,
                access_token: config_1.config.facebook.accessToken,
            }),
        });
        const containerData = await containerResponse.json();
        if (!containerResponse.ok) {
            console.error('Instagram Container Creation Error:', containerData);
            return {
                status: 'ERROR',
                response: {
                    error: containerData.error?.message || 'Container creation failed',
                    code: containerData.error?.code,
                    type: containerData.error?.type
                }
            };
        }
        const creationId = containerData.id;
        console.log('📸 Instagram container created:', creationId);
        // Step 2: Publish the container
        const publishResponse = await fetch(`https://graph.facebook.com/v18.0/${config_1.config.instagram.businessId}/media_publish`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                creation_id: creationId,
                access_token: config_1.config.facebook.accessToken,
            }),
        });
        const publishData = await publishResponse.json();
        if (!publishResponse.ok) {
            console.error('Instagram Publish Error:', publishData);
            return {
                status: 'ERROR',
                response: {
                    error: publishData.error?.message || 'Publish failed',
                    code: publishData.error?.code,
                    type: publishData.error?.type
                }
            };
        }
        console.log('✅ Instagram post published:', publishData.id);
        return { status: 'SUCCESS', response: publishData };
    }
    catch (error) {
        console.error('Instagram API Exception:', error);
        return {
            status: 'ERROR',
            response: { error: error.message }
        };
    }
}
