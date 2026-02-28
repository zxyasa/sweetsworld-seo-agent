#!/usr/bin/env node
/**
 * Social Media API Configuration Tester
 * Usage: node test-api-config.js
 */

require('dotenv').config();

const tests = {
  facebook: async () => {
    const { FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN } = process.env;
    if (!FACEBOOK_PAGE_ID || !FACEBOOK_ACCESS_TOKEN) {
      return { status: '⚠️  NOT CONFIGURED', message: 'Missing Facebook credentials' };
    }

    try {
      const response = await fetch(
        `https://graph.facebook.com/v18.0/${FACEBOOK_PAGE_ID}?fields=name,access_token&access_token=${FACEBOOK_ACCESS_TOKEN}`
      );
      const data = await response.json();

      if (data.error) {
        return { status: '❌ FAILED', message: data.error.message };
      }
      return { status: '✅ SUCCESS', message: `Page: ${data.name}` };
    } catch (error) {
      return { status: '❌ ERROR', message: error.message };
    }
  },

  instagram: async () => {
    const { INSTAGRAM_BUSINESS_ID, FACEBOOK_ACCESS_TOKEN } = process.env;
    if (!INSTAGRAM_BUSINESS_ID || !FACEBOOK_ACCESS_TOKEN) {
      return { status: '⚠️  NOT CONFIGURED', message: 'Missing Instagram credentials' };
    }

    try {
      const response = await fetch(
        `https://graph.facebook.com/v18.0/${INSTAGRAM_BUSINESS_ID}?fields=username&access_token=${FACEBOOK_ACCESS_TOKEN}`
      );
      const data = await response.json();

      if (data.error) {
        return { status: '❌ FAILED', message: data.error.message };
      }
      return { status: '✅ SUCCESS', message: `Username: @${data.username}` };
    } catch (error) {
      return { status: '❌ ERROR', message: error.message };
    }
  },

  x: async () => {
    const { X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN } = process.env;

    // Check for OAuth 1.0a credentials (required for posting)
    if (!X_API_KEY || !X_API_SECRET || !X_ACCESS_TOKEN || !X_ACCESS_TOKEN_SECRET) {
      if (X_BEARER_TOKEN) {
        return { status: '⚠️  PARTIAL CONFIG', message: 'Bearer Token found, but OAuth 1.0a credentials needed for posting' };
      }
      return { status: '⚠️  NOT CONFIGURED', message: 'Missing X OAuth credentials (API Key, Secret, Access Token)' };
    }

    try {
      // Use Bearer Token for user verification if available, otherwise OAuth is needed
      const testToken = X_BEARER_TOKEN || X_ACCESS_TOKEN;
      const response = await fetch(
        'https://api.twitter.com/2/users/me',
        {
          headers: {
            'Authorization': `Bearer ${testToken}`
          }
        }
      );
      const data = await response.json();

      if (data.errors) {
        return { status: '❌ FAILED', message: data.errors[0].message };
      }
      return { status: '✅ SUCCESS', message: `User: @${data.data?.username || 'unknown'} (OAuth configured)` };
    } catch (error) {
      return { status: '❌ ERROR', message: error.message };
    }
  },

  pinterest: async () => {
    const { PINTEREST_ACCESS_TOKEN } = process.env;
    if (!PINTEREST_ACCESS_TOKEN) {
      return { status: '⚠️  NOT CONFIGURED', message: 'Missing Pinterest Access Token' };
    }

    try {
      const response = await fetch(
        'https://api.pinterest.com/v5/user_account',
        {
          headers: {
            'Authorization': `Bearer ${PINTEREST_ACCESS_TOKEN}`
          }
        }
      );
      const data = await response.json();

      if (data.code) {
        return { status: '❌ FAILED', message: data.message };
      }
      return { status: '✅ SUCCESS', message: `User: ${data.username || 'unknown'}` };
    } catch (error) {
      return { status: '❌ ERROR', message: error.message };
    }
  },

  gbp: async () => {
    const { GBP_ACCOUNT_ID, GBP_LOCATION_ID, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_REFRESH_TOKEN } = process.env;
    if (!GBP_ACCOUNT_ID || !GBP_LOCATION_ID || !GOOGLE_OAUTH_CLIENT_ID || !GOOGLE_OAUTH_REFRESH_TOKEN) {
      return { status: '⚠️  NOT CONFIGURED', message: 'Missing GBP credentials' };
    }

    return { status: '⚠️  MANUAL CHECK', message: 'GBP requires additional OAuth flow' };
  }
};

async function main() {
  console.log('\n🔍 Testing Social Media API Configuration...\n');
  console.log('━'.repeat(60));

  const results = [];

  for (const [platform, testFn] of Object.entries(tests)) {
    const platformName = {
      facebook: 'Facebook',
      instagram: 'Instagram',
      x: 'X (Twitter)',
      pinterest: 'Pinterest',
      gbp: 'Google Business Profile'
    }[platform];

    process.stdout.write(`${platformName.padEnd(25)} `);
    const result = await testFn();
    console.log(`${result.status} ${result.message}`);
    results.push({ platform: platformName, ...result });
  }

  console.log('━'.repeat(60));

  const configured = results.filter(r => r.status === '✅ SUCCESS').length;
  const total = results.length;

  console.log(`\n📊 Configuration Status: ${configured}/${total} (${Math.round(configured/total*100)}%)\n`);

  if (configured === 0) {
    console.log('💡 Tip: Check SOCIAL_MEDIA_API_SETUP.md for configuration guide\n');
  } else if (configured < total) {
    console.log('💡 Tip: Some platforms not configured, you can still use configured ones\n');
  } else {
    console.log('🎉 All platforms configured! Set PUBLISH_MODE=live to start publishing\n');
  }
}

main().catch(console.error);
