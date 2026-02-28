"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.translateToAustralianEnglish = translateToAustralianEnglish;
/**
 * Detects if text contains Chinese characters
 */
function containsChinese(text) {
    return /[\u4e00-\u9fa5]/.test(text);
}
/**
 * Translates Chinese text to Australian English using OpenAI
 */
async function translateToAustralianEnglish(title, excerpt) {
    const needsTranslation = containsChinese(title) || containsChinese(excerpt);
    if (!needsTranslation) {
        return { title, excerpt, wasTranslated: false };
    }
    console.log('🌏 Detected Chinese content, translating to Australian English...');
    try {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
            },
            body: JSON.stringify({
                model: 'gpt-4o',
                messages: [
                    {
                        role: 'system',
                        content: `You are a professional translator specializing in Australian English.
Translate Chinese text to natural, engaging Australian English suitable for social media marketing.
Use Australian spelling (e.g., "flavour", "colour", "favourite").
Keep the tone friendly, casual, and authentic to Australian culture.
Preserve any emojis and formatting.`
                    },
                    {
                        role: 'user',
                        content: `Translate the following to Australian English:

Title: ${title}

Excerpt: ${excerpt}

Return ONLY a JSON object with this exact format:
{"title": "translated title", "excerpt": "translated excerpt"}`
                    }
                ],
                temperature: 0.7,
            }),
        });
        const data = await response.json();
        if (!response.ok) {
            console.error('❌ OpenAI translation error:', data);
            throw new Error(data.error?.message || 'Translation failed');
        }
        const content = data.choices[0].message.content.trim();
        const jsonMatch = content.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            throw new Error('Invalid translation response format');
        }
        const translated = JSON.parse(jsonMatch[0]);
        console.log('✅ Translation completed');
        console.log('   Original title:', title);
        console.log('   Translated title:', translated.title);
        return {
            title: translated.title,
            excerpt: translated.excerpt,
            wasTranslated: true,
        };
    }
    catch (error) {
        console.error('❌ Translation failed:', error.message);
        console.log('⚠️  Falling back to original content');
        return { title, excerpt, wasTranslated: false };
    }
}
