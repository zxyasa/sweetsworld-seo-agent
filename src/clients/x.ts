import { config } from '../config';
import crypto from 'crypto';

// OAuth 1.0a signature generation
function generateOAuthSignature(
  method: string,
  url: string,
  params: Record<string, string>,
  consumerSecret: string,
  tokenSecret: string
): string {
  // Sort parameters
  const sortedParams = Object.keys(params)
    .sort()
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');

  // Create signature base string
  const signatureBaseString = [
    method.toUpperCase(),
    encodeURIComponent(url),
    encodeURIComponent(sortedParams)
  ].join('&');

  // Create signing key
  const signingKey = `${encodeURIComponent(consumerSecret)}&${encodeURIComponent(tokenSecret)}`;

  // Generate signature
  const signature = crypto
    .createHmac('sha1', signingKey)
    .update(signatureBaseString)
    .digest('base64');

  return signature;
}

// Generate OAuth 1.0a authorization header
function generateOAuthHeader(
  method: string,
  url: string,
  body: any,
  consumerKey: string,
  consumerSecret: string,
  accessToken: string,
  accessTokenSecret: string
): string {
  const oauthParams: Record<string, string> = {
    oauth_consumer_key: consumerKey,
    oauth_token: accessToken,
    oauth_signature_method: 'HMAC-SHA1',
    oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
    oauth_nonce: crypto.randomBytes(32).toString('base64').replace(/\W/g, ''),
    oauth_version: '1.0',
  };

  // For POST requests, we don't include body params in signature
  const signature = generateOAuthSignature(method, url, oauthParams, consumerSecret, accessTokenSecret);
  oauthParams.oauth_signature = signature;

  // Build OAuth header
  const oauthHeader = 'OAuth ' + Object.keys(oauthParams)
    .sort()
    .map(key => `${encodeURIComponent(key)}="${encodeURIComponent(oauthParams[key])}"`)
    .join(', ');

  return oauthHeader;
}

export async function postToX(text: string): Promise<{ status: string; response?: any }> {
  const { apiKey, apiSecret, accessToken, accessTokenSecret } = config.x;

  if (!apiKey || !apiSecret || !accessToken || !accessTokenSecret) {
    return {
      status: 'NOT_CONFIGURED',
      response: { error: 'X API credentials not configured. Need OAuth 1.0a credentials (API Key, API Secret, Access Token, Access Token Secret)' }
    };
  }

  try {
    const url = 'https://api.twitter.com/2/tweets';
    const body = { text };

    // Generate OAuth 1.0a authorization header
    const authHeader = generateOAuthHeader(
      'POST',
      url,
      body,
      apiKey,
      apiSecret,
      accessToken,
      accessTokenSecret
    );

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('X API Error:', data);
      return {
        status: 'ERROR',
        response: {
          error: data.detail || data.title || 'Tweet failed',
          errors: data.errors
        }
      };
    }

    console.log('✅ X tweet posted:', data.data?.id);
    return { status: 'SUCCESS', response: data };
  } catch (error: any) {
    console.error('X API Exception:', error);
    return {
      status: 'ERROR',
      response: { error: error.message }
    };
  }
}