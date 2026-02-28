# Pinterest API Setup Guide

## Step 1: Create a Pinterest Business Account

1. Go to [Pinterest Business](https://business.pinterest.com/)
2. If you don't have a business account, convert your personal account:
   - Go to Settings → Account Management
   - Click "Convert to business account"
   - Fill in your business information

## Step 2: Create a Pinterest App

1. Visit [Pinterest Developers](https://developers.pinterest.com/)
2. Log in with your Pinterest account
3. Click **My Apps** → **Create App**
4. Fill in the app information:
   - App name: "Sweetsworld Content Agent"
   - App description: "Automated content publishing for sweetsworld.com.au"
   - Privacy policy URL: https://sweetsworld.com.au/privacy-policy/
   - Website URL: https://sweetsworld.com.au
5. Click **Create**

## Step 3: Generate Access Token

1. Go to your app dashboard
2. Click on the **OAuth** tab
3. Click **Generate** next to "Access token"
4. Make sure the following scopes are selected:
   - `boards:read` - Read boards
   - `boards:write` - Create and edit boards
   - `pins:read` - Read pins
   - `pins:write` - Create and edit pins
5. Click **Generate token**
6. **IMPORTANT**: Copy the access token immediately (it's only shown once)

## Step 4: Add to Your .env File

Add the access token to your `.env` file:

```env
PINTEREST_ACCESS_TOKEN=pina_your_access_token_here
```

## Step 5: Test the Configuration

Run the test script to verify Pinterest is configured:

```bash
node test-api-config.js
```

You should see:
```
Pinterest    ✅ SUCCESS User: yourusername
```

## Important Notes

- Pinterest requires an **image** for all pins - text-only posts won't work
- The system will automatically use your first board for posting
- Make sure you have at least one board created on Pinterest
- Access tokens don't expire unless you revoke them

## Troubleshooting

### "No boards found" error
- Create at least one board on Pinterest
- Make sure your access token has `boards:read` permission

### "Invalid access token" error
- Regenerate a new access token
- Make sure you copied the entire token
- Check that your Pinterest app is active

### "Image required" error
- Pinterest requires all pins to have images
- Make sure your WordPress posts have featured images
- The image URL must be publicly accessible

## Next Steps

Once Pinterest is configured:
1. Test with dry_run mode first: `PUBLISH_MODE=dry_run`
2. When ready, switch to live mode: `PUBLISH_MODE=live`
3. All WordPress posts with featured images will be automatically posted to Pinterest
