# TikTok Content Posting API Application Guide

Complete checklist and materials for applying for TikTok Content Posting API access.

---

## ✅ Pre-Application Checklist

Before applying, make sure you have:

- [ ] **TikTok Business Account** (converted from personal account)
- [ ] **TikTok Developer Account** (registered at developers.tiktok.com)
- [ ] **Business Website** (sweetsworld.com.au - ✅ you have this)
- [ ] **Clear use case** for Content Posting API
- [ ] **Privacy Policy** on your website
- [ ] **Terms of Service** on your website

---

## Step 1: Convert to TikTok Business Account

### On Mobile App:

1. Open TikTok app
2. Go to **Profile** → **☰ Menu** (top right)
3. Tap **Settings and privacy**
4. Tap **Manage account**
5. Tap **Switch to Business Account**
6. Choose category: **Retail** or **Food & Beverage**
7. Complete the setup

✅ **Status**: Complete this first before proceeding

---

## Step 2: Register as TikTok Developer

1. Visit [TikTok for Developers](https://developers.tiktok.com/)
2. Click **Register** or **Sign in**
3. Log in with your TikTok Business Account
4. Accept Terms of Service
5. Verify your email

✅ **Status**: Should take 5 minutes

---

## Step 3: Create Your App

### App Details to Prepare:

**App Name:**
```
Sweetsworld Content Automation
```

**App Type:**
```
Web App
```

**App Description:**
```
Automated content distribution system for Sweetsworld.com.au,
an Australian online candy and confectionery store. This app
automatically creates and publishes short-form video content
from our blog posts to engage with our TikTok audience.
```

**Website URL:**
```
https://sweetsworld.com.au
```

**Redirect URI:**
```
https://sweetsworld.com.au/tiktok/callback
```
*Note: This can be a placeholder - TikTok requires it but for server-to-server auth it's not used*

**Privacy Policy URL:**
```
https://sweetsworld.com.au/privacy-policy/
```
*Note: Make sure you have this page on your website*

**Terms of Service URL:**
```
https://sweetsworld.com.au/terms-of-service/
```

---

## Step 4: Apply for Content Posting API

After creating your app, you need to request access to the Content Posting API product.

### Application Form Answers:

**Product Name:**
```
Content Posting API
```

**Use Case Description:**
```
Sweetsworld.com.au is an Australian e-commerce store specializing
in candy, chocolate, and confectionery products. We regularly
publish educational blog posts about our products, recipes, and
candy-related content.

We want to automatically convert our blog posts into short-form
videos using AI technology and post them to TikTok to:

1. Engage with our TikTok audience
2. Drive traffic to our e-commerce store
3. Educate customers about our products
4. Share recipes and candy-related tips
5. Build brand awareness in the Australian market

Our system will:
- Use AI to generate talking-head videos from blog content
- Post 1-5 videos per day (matching our blog publishing schedule)
- Include product information and educational content
- Drive engagement with the candy/confectionery community on TikTok
```

**Monthly Active Users (MAU):**
```
100 - 1,000
```
*Start conservatively - you can always increase later*

**Daily Video Posts:**
```
1 - 5 videos per day
```
*Based on your blog posting frequency*

**Countries/Regions:**
```
Australia (primary)
```

**Business Model:**
```
E-commerce / Retail
```

**Industry:**
```
Food & Beverage / Retail / E-commerce
```

**How will you use the API?**
```
Automated posting: Our server-side application will automatically:

1. Detect when a new blog post is published on sweetsworld.com.au
2. Extract the blog title and excerpt
3. Generate a short video (15-60 seconds) using AI text-to-video
   technology (D-ID API)
4. Post the video to TikTok via Content Posting API
5. Use appropriate hashtags and descriptions
6. Link back to our website for more information

The content will be:
- Educational (candy facts, recipes, product information)
- Engaging (AI presenter with Australian English voice)
- Authentic (reflecting our brand voice)
- Compliant with TikTok Community Guidelines
```

**Technical Implementation:**
```
- Server-side Node.js application
- OAuth 2.0 authentication
- Direct Post API endpoint
- Video format: MP4, vertical 9:16 ratio
- Compliance: All content follows TikTok guidelines
- Privacy: No user data collection, only posting to our own account
```

**Expected Monthly API Calls:**
```
30 - 150 video posts per month
(1-5 posts per day × 30 days)
```

**Will you collect user data?**
```
No - We only post to our own business account.
We do not collect any user data from TikTok.
```

**Privacy & Data Handling:**
```
We do not collect, store, or process any user data from TikTok.
We only use the Content Posting API to publish videos to our
own business account. All content is created by our own systems
and complies with TikTok's Community Guidelines and Terms of Service.
```

---

## Step 5: Supporting Documents

TikTok may request additional documentation:

### Prepare These:

1. **Business Registration**
   - If you have an ABN (Australian Business Number), provide it
   - Business name: Sweetsworld / Kards & Kandy

2. **Website Screenshots**
   - Screenshot of sweetsworld.com.au homepage
   - Screenshot of blog section
   - Screenshot of privacy policy

3. **Sample Content**
   - Example of the type of videos you'll post
   - Show them the D-ID generated video from our test

4. **Use Case Diagram** (optional but helpful)
   ```
   WordPress Blog Post → AI Video Generation → TikTok API → Published Video
   ```

---

## Step 6: Approval Timeline

**Typical Timeline:**
- Application submission: Immediate
- Initial review: 3-5 business days
- Additional questions (if any): 1-2 weeks
- Final approval: 1-2 weeks total

**During Trial Access:**
- You can test the API
- Videos will be **private** (only visible to you)
- Daily upload limit: ~15 videos
- Rate limits apply

**After Production Approval:**
- Videos can be **public**
- Same upload limits
- Full API access

---

## Step 7: After Approval

Once approved, you'll receive:

1. **Client Key** (App ID)
2. **Client Secret**
3. **Access to generate Access Token**

### Generate Access Token:

1. Go to your app dashboard
2. Click **Generate Access Token**
3. Select scope: **video.publish**
4. Authorize with your TikTok account
5. Copy the access token

Add to `.env`:
```env
TIKTOK_CLIENT_KEY=your_client_key_here
TIKTOK_CLIENT_SECRET=your_client_secret_here
TIKTOK_ACCESS_TOKEN=your_access_token_here
```

---

## ⚠️ Common Issues & Tips

### Issue: Application Rejected

**Reasons:**
- Insufficient use case description
- No privacy policy on website
- Unclear business model

**Solution:**
- Provide more detailed use case
- Add/update privacy policy
- Clarify you're posting to your own account only

### Issue: Stuck in Review

**Solution:**
- Wait patiently (can take 1-2 weeks)
- Check email for TikTok requests
- Respond promptly to any questions

### Issue: Trial Access Only

**This is normal!**
- Start with Trial Access
- Videos will be private
- Test thoroughly
- Apply for Production Access later

---

## 📝 Quick Application Template

Copy and paste this when applying:

```
App Name: Sweetsworld Content Automation

Use Case: E-commerce content distribution - Converting blog
posts from sweetsworld.com.au (Australian candy store) into
short-form educational videos using AI, posting 1-5 videos
daily to engage TikTok audience.

MAU: 100-1,000
Daily Posts: 1-5 videos
Industry: Food & Beverage / E-commerce
Region: Australia

Technical: Server-side Node.js, OAuth 2.0, Direct Post API
Data Collection: None - posting to own business account only

Purpose: Drive traffic to e-commerce store, educate customers
about candy products, share recipes, build brand awareness.
```

---

## ✅ Post-Approval Testing Checklist

After approval:

- [ ] Add credentials to `.env`
- [ ] Test in dry_run mode first
- [ ] Verify video generation works
- [ ] Check video format (9:16, MP4)
- [ ] Test with 1-2 posts
- [ ] Monitor for errors
- [ ] Switch to live mode
- [ ] Set up monitoring

---

## 🎯 Summary

**Total Time Required:**
- App setup: 30 minutes
- Application: 15 minutes
- Approval wait: 1-2 weeks

**Success Rate:**
- High if you clearly explain use case
- E-commerce/retail apps usually approved
- Be honest and transparent

**After Approval:**
- 5 minutes to add credentials
- Immediate testing capability
- Full automation ready!

---

**Next Steps:**
1. ✅ Complete TikTok Business Account conversion
2. ✅ Register as TikTok Developer
3. ✅ Create app with details above
4. ✅ Apply for Content Posting API access
5. ⏳ Wait for approval (1-2 weeks)
6. ✅ Add credentials and test
7. 🚀 Enjoy automated TikTok posting!

Good luck! 🍀
