# TikTok + D-ID AI Video Setup Guide

This guide will help you set up automated TikTok posting with AI-generated videos using D-ID.

---

## Part 1: D-ID API Setup (Video Generation)

### Step 1: Create D-ID Account

1. Go to [D-ID](https://www.d-id.com/)
2. Sign up for an account
3. You get **20 free credits** to start (enough for ~15-20 videos)

### Step 2: Get API Key

1. Go to [D-ID API Settings](https://studio.d-id.com/account-settings)
2. Navigate to **API** tab
3. Click **Create API Key**
4. Copy your API key (starts with `Basic ...`)

### Step 3: Add to .env

```env
DID_API_KEY=Basic_your_api_key_here
```

### Pricing

- **Trial**: 20 credits free (~15-20 videos)
- **Lite**: $5.6/month (15 videos)
- **Pro**: $29.7/month (90 videos)
- **Pay-as-you-go**: $0.04-0.20 per video

**Recommended**: Start with free trial, then Pay-as-you-go ($0.80-4/month for 20 videos)

---

## Part 2: TikTok API Setup

### Step 1: Convert to Business Account

1. Open TikTok app on your phone
2. Go to **Profile** → **Settings**
3. Tap **Manage account**
4. Select **Switch to Business Account**
5. Choose a category (e.g., "Retail")

### Step 2: Create TikTok Developer Account

1. Go to [TikTok for Developers](https://developers.tiktok.com/)
2. Click **Register** or **Log In**
3. Complete developer registration
4. Verify your email

### Step 3: Create an App

1. Go to [TikTok Developer Portal](https://developers.tiktok.com/apps)
2. Click **+ Create new app**
3. Fill in app details:
   - **App name**: "Sweetsworld Content Agent"
   - **App type**: Web
   - **Redirect URI**: `https://sweetsworld.com.au/tiktok/callback`
   - **Website URL**: `https://sweetsworld.com.au`

### Step 4: Request Content Posting API Access

1. In your app dashboard, go to **Products**
2. Find **Content Posting API**
3. Click **Add product**
4. Fill out the application form:
   - **Use case**: "Automated content distribution from e-commerce blog"
   - **Monthly active users**: "100-1000"
   - **Daily video posts**: "1-5 per day"
5. Submit application

⚠️ **Important**: Approval takes 1-2 weeks. You'll receive an email when approved.

### Step 5: Get Credentials (After Approval)

Once approved:

1. Go to your app → **Manage apps**
2. Note down:
   - **Client Key**
   - **Client Secret**
3. Click **Generate access token**
4. Select scope: **video.publish**
5. Authorize with your TikTok account
6. Copy the **Access Token**

### Step 6: Add to .env

```env
TIKTOK_CLIENT_KEY=your_client_key_here
TIKTOK_CLIENT_SECRET=your_client_secret_here
TIKTOK_ACCESS_TOKEN=your_access_token_here
```

---

## Part 3: Testing

### Test D-ID Video Generation

Create a test file `test-did.js`:

```javascript
require('dotenv').config();

async function testDID() {
  const response = await fetch('https://api.d-id.com/talks', {
    method: 'POST',
    headers: {
      'Authorization': process.env.DID_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      script: {
        type: 'text',
        input: 'G\'day! Welcome to Sweetsworld, your favourite Australian candy store!',
        provider: {
          type: 'microsoft',
          voice_id: 'en-AU-NatashaNeural',
        },
      },
      source_url: 'https://d-id-public-bucket.s3.amazonaws.com/alice.jpg',
    }),
  });

  const data = await response.json();
  console.log('D-ID Response:', data);
}

testDID().catch(console.error);
```

Run: `node test-did.js`

Expected output:
```json
{
  "id": "tlk_xxx...",
  "status": "created"
}
```

### Test Complete Workflow

With the server running (`npm run dev`), test with:

```bash
curl -X POST http://localhost:8787/webhook/wp \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Amazing Australian Chocolate",
    "slug": "amazing-australian-chocolate",
    "url": "https://sweetsworld.com.au/candy/amazing-chocolate/",
    "excerpt": "Discover the finest Australian chocolate treats!",
    "image": "https://sweetsworld.com.au/images/chocolate.jpg"
  }'
```

This will:
1. ✅ Generate content for all platforms
2. ✅ Generate a video using D-ID (takes ~30 seconds)
3. ✅ Post to TikTok (if PUBLISH_MODE=live)
4. ✅ Post to Facebook, Instagram, Pinterest

---

## Part 4: How It Works

### Workflow

```
WordPress Post Published
    ↓
Webhook → sweetsworld-seo-agent
    ↓
Extract: title, excerpt, image
    ↓
Generate Social Content (all platforms)
    ↓
For TikTok:
    ├─ Check if video exists
    │   └─ If NO → Call D-ID API
    │       ├─ Create talking head video
    │       ├─ Wait for generation (~30 sec)
    │       └─ Get video URL
    ↓
Post to TikTok API
    ├─ Upload video
    ├─ Wait for processing
    └─ Publish
    ↓
Also post to:
    ├─ Facebook (text + image)
    ├─ Instagram (image + caption)
    ├─ Pinterest (pin with image)
    └─ X, GBP (if configured)
```

### Video Generation

- **Voice**: Australian English female (en-AU-NatashaNeural)
- **Presenter**: Default D-ID avatar (professional looking)
- **Script**: Auto-generated from blog title + excerpt
- **Duration**: ~15-30 seconds
- **Format**: Vertical 9:16 (TikTok format)

---

## Part 5: Cost Breakdown

### Monthly Cost (20 blog posts/month)

| Service | Cost/Video | Monthly Cost | Notes |
|---------|------------|--------------|-------|
| D-ID API | $0.04-0.20 | **$0.80-$4** | Pay-as-you-go |
| TikTok API | Free | **$0** | Free after approval |
| **Total** | - | **$0.80-$4/month** | Very affordable! |

Compare to alternatives:
- Synthesia: $29/month minimum
- Pictory: $23/month minimum
- Manual video creation: Hours of time

---

## Part 6: Limitations & Requirements

### D-ID Limitations
- Trial: 20 credits free
- Video length: Max 5 minutes (we use 15-30 sec)
- Generation time: 30-60 seconds per video

### TikTok Limitations
- **Requires approval** (1-2 weeks wait)
- Daily upload limit: ~15 videos per account
- Videos must be public during trial (private until production approved)
- Minimum video length: 3 seconds
- Maximum video length: 10 minutes

### Content Requirements
- Blog posts should have clear titles and excerpts
- Australian English style recommended
- Keep content engaging and authentic

---

## Part 7: Troubleshooting

### "D-ID API key not configured"
- Check .env has `DID_API_KEY=Basic_...`
- Make sure you included "Basic " prefix

### "Video generation timed out"
- D-ID servers might be slow
- Try again in a few minutes
- Check D-ID dashboard for errors

### "TikTok API credentials not configured"
- Ensure you've been approved for Content Posting API
- Check .env has all three TikTok credentials
- Verify access token hasn't expired

### "Your application consumer type is not supported"
- You're still in Trial Access
- Need to apply for Standard Access
- Contact TikTok support if approved but still seeing error

### Videos are private on TikTok
- This is normal during Trial Access
- Apply for Production Access to post public videos
- Private videos are still useful for testing

---

## Part 8: Best Practices

1. **Start in dry_run mode**
   - Test thoroughly before going live
   - Check generated content quality

2. **Monitor costs**
   - D-ID credits usage in dashboard
   - Start with free trial

3. **Content quality**
   - Write engaging blog excerpts (they become video scripts)
   - Keep titles concise and catchy
   - Use high-quality featured images

4. **TikTok strategy**
   - Post 1-3 times per day max
   - Use trending hashtags
   - Engage with comments

5. **Iterate and improve**
   - Review video quality
   - Adjust scripts if needed
   - Test different presenters

---

## Summary

You now have:
- ✅ AI video generation from blog posts
- ✅ Automated TikTok posting
- ✅ Multi-platform distribution (Facebook, Instagram, Pinterest, TikTok)
- ✅ Australian English content
- ✅ UTM tracking for analytics

**Next steps:**
1. Get D-ID API key (5 minutes)
2. Apply for TikTok Content Posting API (wait 1-2 weeks)
3. Test in dry_run mode
4. Switch to live mode when ready

**Cost**: $0.80-4/month for 20 videos - very affordable!
