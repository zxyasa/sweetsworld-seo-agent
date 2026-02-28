import { config } from '../config';

/**
 * D-ID AI Video Generation Client
 *
 * Generates talking head videos from text using D-ID API
 * Documentation: https://docs.d-id.com/reference/talks
 */

export interface VideoGenerationOptions {
  script: string;
  voice?: string; // default: 'en-US-JennyNeural'
  presenter?: string; // default: 'amy' or custom presenter image URL
}

export interface VideoGenerationResult {
  status: string;
  videoUrl?: string;
  id?: string;
  error?: string;
}

/**
 * Generate a video from text using D-ID API
 */
export async function generateVideo(options: VideoGenerationOptions): Promise<VideoGenerationResult> {
  if (!config.did.apiKey) {
    return {
      status: 'NOT_CONFIGURED',
      error: 'D-ID API key not configured'
    };
  }

  const { script, voice = 'en-AU-NatashaNeural', presenter = 'amy' } = options;

  try {
    console.log('🎬 Creating D-ID video generation task...');

    // Step 1: Create a talk (video generation task)
    const createResponse = await fetch('https://api.d-id.com/talks', {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${config.did.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        script: {
          type: 'text',
          input: script,
          provider: {
            type: 'microsoft',
            voice_id: voice,
          },
        },
        config: {
          fluent: true,
          pad_audio: 0,
        },
        source_url: presenter === 'amy'
          ? 'https://d-id-public-bucket.s3.amazonaws.com/alice.jpg'
          : presenter,
      }),
    });

    if (!createResponse.ok) {
      const errorData = await createResponse.json();
      console.error('D-ID Creation Error:', errorData);
      return {
        status: 'ERROR',
        error: errorData.message || 'Failed to create video'
      };
    }

    const createData = await createResponse.json();
    const videoId = createData.id;
    console.log(`📹 Video generation started: ${videoId}`);

    // Step 2: Poll for completion
    const maxAttempts = 60; // 2 minutes max (2 second intervals)
    let attempts = 0;

    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds

      const statusResponse = await fetch(`https://api.d-id.com/talks/${videoId}`, {
        headers: {
          'Authorization': `Basic ${config.did.apiKey}`,
        },
      });

      if (!statusResponse.ok) {
        const errorData = await statusResponse.json();
        console.error('D-ID Status Check Error:', errorData);
        return {
          status: 'ERROR',
          error: 'Failed to check video status'
        };
      }

      const statusData = await statusResponse.json();

      if (statusData.status === 'done') {
        console.log('✅ Video generation completed:', statusData.result_url);
        return {
          status: 'SUCCESS',
          videoUrl: statusData.result_url,
          id: videoId
        };
      } else if (statusData.status === 'error') {
        console.error('D-ID Generation Failed:', statusData.error);
        return {
          status: 'ERROR',
          error: statusData.error || 'Video generation failed'
        };
      }

      attempts++;
      console.log(`⏳ Video generation in progress... (${attempts}/${maxAttempts})`);
    }

    return {
      status: 'TIMEOUT',
      error: 'Video generation timed out after 2 minutes'
    };

  } catch (error: any) {
    console.error('D-ID API Exception:', error);
    return {
      status: 'ERROR',
      error: error.message
    };
  }
}

/**
 * Generate a video for social media from blog post excerpt
 */
export async function generateSocialVideo(title: string, excerpt: string): Promise<VideoGenerationResult> {
  // Create a concise script for TikTok (max 60 seconds)
  const script = `G'day! ${title}. ${excerpt.substring(0, 200)}. Visit Sweetsworld.com.au for more!`;

  return generateVideo({
    script,
    voice: 'en-AU-NatashaNeural', // Australian English female voice
    presenter: 'amy', // Default D-ID presenter
  });
}
