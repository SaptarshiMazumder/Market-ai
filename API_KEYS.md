# How to Get Your API Keys

Quick reference for obtaining the required API keys.

## 1. HeyGen (Required)

**What it does:** Generates realistic AI avatar videos

**Get your key:**
1. Visit: [https://app.heygen.com/](https://app.heygen.com/)
2. Sign up (email or Google)
3. Go to Settings → API Keys
4. Click "Create API Key"
5. Copy and save your key

**Free Trial:** Yes, with limited credits
**Cost:** ~$1.50 per video (30 seconds)
**Best For:** Professional avatar videos

---

## 2. ElevenLabs (Required)

**What it does:** Generates professional AI voiceovers

**Get your key:**
1. Visit: [https://elevenlabs.io/](https://elevenlabs.io/)
2. Create an account
3. Click your profile picture
4. Go to "Profile + API Key"
5. Copy your API key

**Free Trial:** 10,000 characters/month
**Cost:** ~$0.10 per video voiceover
**Best For:** Natural-sounding voices

---

## 3. RunwayML (Optional)

**What it does:** Enhances videos with AI-generated product visuals

**Get your key:**
1. Visit: [https://runwayml.com/](https://runwayml.com/)
2. Sign up for an account
3. Go to Account Settings → API Keys
4. Generate new API key
5. Copy your key

**Free Trial:** Limited credits
**Cost:** ~$0.05 per second
**Note:** Optional - system works without it

---

## Setting Up Your Keys

Once you have your keys, add them to `backend/.env`:

```env
HEYGEN_API_KEY=your_heygen_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
RUNWAYML_API_KEY=your_runwayml_api_key_here
```

**Important:**
- No quotes needed around the keys
- No spaces before or after the `=`
- Keep these keys private and never commit them to git

---

## Cost Summary

For 10 marketing videos (30 seconds each):

| Service | Cost |
|---------|------|
| HeyGen | ~$15 |
| ElevenLabs | ~$1 |
| **Total** | **~$16** |

**Free tier testing:** You can create 2-5 videos for free using trial credits!

---

## Troubleshooting

**Invalid API Key Error:**
- Double-check you copied the entire key
- Ensure no extra spaces
- Try regenerating the key

**Rate Limit Error:**
- You've exceeded the free tier
- Upgrade your plan or wait for reset
- Check your account dashboard

**No Credits Available:**
- Add credits to your account
- Free tier has limited usage
- Upgrade to a paid plan

---

## Alternative Services

If you want to explore alternatives:

**Instead of HeyGen:**
- D-ID ([https://www.d-id.com/](https://www.d-id.com/))
- Synthesia ([https://www.synthesia.io/](https://www.synthesia.io/))

**Instead of ElevenLabs:**
- Play.ht ([https://play.ht/](https://play.ht/))
- Murf AI ([https://murf.ai/](https://murf.ai/))

Note: You would need to modify the API integration code to use these alternatives.
