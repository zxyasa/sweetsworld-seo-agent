import { config } from '../config';

export async function postToFacebook(message: string): Promise<{ status: string; response?: any }> {
  if (!config.facebook.accessToken || !config.facebook.pageId) {
    return { status: 'NOT_CONFIGURED', response: { error: 'Facebook credentials not configured' } };
  }

  try {
    const response = await fetch(
      `https://graph.facebook.com/v18.0/${config.facebook.pageId}/feed`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          access_token: config.facebook.accessToken,
        }),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      console.error('Facebook API Error:', data);
      return {
        status: 'ERROR',
        response: {
          error: data.error?.message || 'Unknown error',
          code: data.error?.code,
          type: data.error?.type
        }
      };
    }

    console.log('✅ Facebook post published:', data.id);
    return { status: 'SUCCESS', response: data };
  } catch (error: any) {
    console.error('Facebook API Exception:', error);
    return {
      status: 'ERROR',
      response: { error: error.message }
    };
  }
}