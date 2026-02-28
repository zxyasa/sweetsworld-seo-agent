"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.postToPinterest = postToPinterest;
const config_1 = require("../config");
async function postToPinterest(title, description, link, imageUrl) {
    if (!config_1.config.pinterest.accessToken) {
        return { status: 'NOT_CONFIGURED', response: { error: 'Pinterest credentials not configured' } };
    }
    // Pinterest requires an image
    if (!imageUrl) {
        console.log('⚠️  Pinterest pin skipped: No image provided (Pinterest requires images)');
        return { status: 'SKIPPED', response: { error: 'Pinterest requires an image URL' } };
    }
    try {
        // Get the default board ID (we'll use the first board)
        const boardsResponse = await fetch('https://api.pinterest.com/v5/boards', {
            headers: {
                'Authorization': `Bearer ${config_1.config.pinterest.accessToken}`,
            },
        });
        if (!boardsResponse.ok) {
            const boardsError = await boardsResponse.json();
            console.error('Pinterest Boards Error:', boardsError);
            return {
                status: 'ERROR',
                response: {
                    error: boardsError.message || 'Failed to fetch boards',
                    code: boardsError.code
                }
            };
        }
        const boardsData = await boardsResponse.json();
        const boards = boardsData.items || [];
        if (boards.length === 0) {
            console.error('No Pinterest boards found');
            return {
                status: 'ERROR',
                response: { error: 'No Pinterest boards available. Please create a board first.' }
            };
        }
        const boardId = boards[0].id;
        console.log(`📌 Using Pinterest board: ${boards[0].name} (${boardId})`);
        // Create a Pin
        const pinResponse = await fetch('https://api.pinterest.com/v5/pins', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config_1.config.pinterest.accessToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: title,
                description: description,
                link: link,
                media_source: {
                    source_type: 'image_url',
                    url: imageUrl,
                },
                board_id: boardId,
            }),
        });
        const pinData = await pinResponse.json();
        if (!pinResponse.ok) {
            console.error('Pinterest Pin Creation Error:', pinData);
            return {
                status: 'ERROR',
                response: {
                    error: pinData.message || 'Pin creation failed',
                    code: pinData.code
                }
            };
        }
        console.log('✅ Pinterest pin created:', pinData.id);
        return { status: 'SUCCESS', response: pinData };
    }
    catch (error) {
        console.error('Pinterest API Exception:', error);
        return {
            status: 'ERROR',
            response: { error: error.message }
        };
    }
}
