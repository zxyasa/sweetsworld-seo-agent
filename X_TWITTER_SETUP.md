# X (Twitter) API Setup Guide

## Important: X API Pricing

⚠️ **X API is no longer free for posting tweets.**

### Pricing Tiers (2026):
- **Free**: Read-only access (cannot post tweets)
- **Basic ($100/month)**: Can post up to 1,500 tweets per month, read access
- **Pro ($5,000/month)**: Higher limits, full access

**For automated posting, you need at least the Basic tier ($100/month).**

---

## Step 1: Create X Developer Account

1. Go to [X Developer Portal](https://developer.twitter.com/)
2. Log in with your X account
3. Click **Sign up** for developer access
4. Complete the application form:
   - Use case: "Automated content distribution for e-commerce"
   - Company: "Sweetsworld"
   - Website: https://sweetsworld.com.au

---

## Step 2: Subscribe to Basic Access

1. Once approved, go to [Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Click **Products** → **Basic**
3. Subscribe to Basic tier ($100/month)
4. Confirm payment

---

## Step 3: Create an App

1. Go to **Projects & Apps** → **Create App**
2. Fill in app details:
   - App name: "Sweetsworld Content Agent"
   - App description: "Automated content distribution for sweetsworld.com.au"

---

## Step 4: Get API Credentials

### Option A: Using OAuth 2.0 (Recommended)

1. Go to your app → **Keys and tokens**
2. Under **OAuth 2.0 Client ID and Client Secret**, click **Generate**
3. Save your **Client ID** and **Client Secret**

4. Set up authentication:
   ```bash
   # Install the X API library
   npm install twitter-api-v2
   ```

5. You'll need to implement OAuth 2.0 flow to get an access token

### Option B: Using Bearer Token (Simpler, but limited)

1. Go to your app → **Keys and tokens**
2. Under **Bearer Token**, click **Generate**
3. Copy the Bearer Token (starts with `AAAA...`)

⚠️ **Note**: Bearer Token alone has read-only access. For posting, you need OAuth 1.0a or OAuth 2.0.

---

## Step 5: Set Up OAuth 1.0a (For Posting Tweets)

For posting tweets, you need OAuth 1.0a credentials:

1. Go to your app → **Keys and tokens**
2. Under **Consumer Keys**, click **Generate**
   - Copy **API Key** (Consumer Key)
   - Copy **API Secret** (Consumer Secret)

3. Under **Authentication Tokens**, click **Generate**
   - Copy **Access Token**
   - Copy **Access Token Secret**

4. Add to your `.env` file:
   ```env
   X_API_KEY=your_api_key_here
   X_API_SECRET=your_api_secret_here
   X_ACCESS_TOKEN=your_access_token_here
   X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
   ```

---

## Step 6: Update App Permissions

1. Go to your app → **Settings**
2. Under **User authentication settings**, click **Set up**
3. Select **Read and write** permissions
4. Save changes

---

## Step 7: Test Configuration

Run the test script:

```bash
node test-api-config.js
```

You should see:
```
X (Twitter)    ✅ SUCCESS User: @yourusername
```

---

## Alternative: Free Options

If you don't want to pay $100/month, consider these alternatives:

### 1. Manual Posting
- Post tweets manually when WordPress publishes
- Use X's web interface or mobile app

### 2. Zapier Integration
- Use Zapier's X integration (included in paid plans)
- Set up: WordPress RSS → Zapier → X
- Cost: ~$20/month for Zapier

### 3. Buffer or Hootsuite
- Social media management tools with X access
- Schedule and auto-post content
- Cost: $15-30/month

### 4. RSS to Twitter Services
- dlvr.it (free tier available)
- IFTTT (limited free tier)
- Connects your WordPress RSS feed to X

---

## Important Notes

- **Free tier cannot post tweets** - only read access
- Basic tier ($100/month) allows 1,500 tweets/month
- Rate limits apply: Be careful not to spam
- X has strict rules about automation - read their [Automation Rules](https://help.twitter.com/en/rules-and-policies/twitter-automation)

---

## Next Steps

**If you want to use X API:**
1. Subscribe to Basic tier ($100/month)
2. Generate OAuth 1.0a credentials
3. Add credentials to `.env`
4. Test with the configuration tool

**If $100/month is too expensive:**
1. Use one of the free alternatives above
2. Skip X integration for now
3. Focus on Facebook, Instagram, and Pinterest (once approved)

---

## Troubleshooting

### "Read-only" or "Unauthorized" errors
- Make sure you have Basic tier subscription
- Check that app permissions are set to "Read and write"
- Verify OAuth 1.0a credentials (not just Bearer Token)

### "Rate limit exceeded"
- Basic tier has daily/monthly limits
- Implement rate limiting in your code
- Don't post too frequently

### "Duplicate content" errors
- X blocks duplicate tweets
- Make sure each tweet is unique
- Add timestamps or variation to content
