# MarketAI Setup Guide

Complete guide to get your AI video marketing generator up and running.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.9+** installed ([Download](https://www.python.org/downloads/))
- **Node.js 18+** and npm installed ([Download](https://nodejs.org/))
- **Git** (optional, for cloning)

## API Keys Required

You need API keys from three services. Here's how to get them:

### 1. HeyGen API Key

HeyGen provides the AI avatars for your videos.

**Steps:**
1. Go to [https://app.heygen.com/](https://app.heygen.com/)
2. Sign up for a free account
3. Navigate to **Settings** → **API**
4. Click **Generate API Key**
5. Copy your API key

**Pricing:**
- Free tier: Limited credits for testing
- Paid plans: Starting at $24/month for 15 credits
- Each video costs approximately 1-2 credits

### 2. ElevenLabs API Key

ElevenLabs generates the professional voiceovers.

**Steps:**
1. Go to [https://elevenlabs.io/](https://elevenlabs.io/)
2. Create an account
3. Click on your profile icon → **Profile**
4. Find your API key in the profile settings
5. Copy your API key

**Pricing:**
- Free tier: 10,000 characters/month
- Paid plans: Starting at $5/month for 30,000 characters

### 3. RunwayML API Key (Optional)

RunwayML Gen-3 can enhance videos with product visuals.

**Steps:**
1. Go to [https://runwayml.com/](https://runwayml.com/)
2. Sign up for an account
3. Navigate to **Settings** → **API Keys**
4. Create a new API key
5. Copy your API key

**Pricing:**
- Pay-as-you-go: ~$0.05 per second of video
- This is optional and can be skipped initially

**Note:** RunwayML integration is optional. The system will work without it using HeyGen alone.

## Installation

### Quick Setup (Windows)

1. **Run the setup script:**
   ```bash
   setup.bat
   ```

2. **Add your API keys:**
   - Open `backend\.env` in a text editor
   - Add your API keys:
   ```env
   HEYGEN_API_KEY=your_heygen_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_key_here
   RUNWAYML_API_KEY=your_runwayml_key_here
   ```

3. **Start the application:**
   ```bash
   start.bat
   ```

4. **Open your browser:**
   - Go to [http://localhost:5173](http://localhost:5173)

### Manual Setup

#### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env  # Windows
# or
cp .env.example .env    # Mac/Linux

# Edit .env and add your API keys
notepad .env  # Windows
# or
nano .env     # Mac/Linux

# Create required directories
mkdir uploads generated

# Start backend server
python app.py
```

Backend will run on [http://localhost:5000](http://localhost:5000)

#### Frontend Setup

```bash
# Open new terminal and navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on [http://localhost:5173](http://localhost:5173)

## Testing the Installation

1. Open [http://localhost:5173](http://localhost:5173)
2. You should see the MarketAI interface
3. Check the browser console for any errors
4. Try uploading a test image

## Troubleshooting

### Backend Issues

**Error: Module not found**
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

**Error: API key not configured**
- Verify your `.env` file has the correct API keys
- Ensure there are no extra spaces or quotes around keys
- Restart the backend server after changing `.env`

**Error: Port 5000 already in use**
- Change the port in `backend/app.py` (line: `app.run(port=5000)`)
- Update the proxy in `frontend/vite.config.js` accordingly

### Frontend Issues

**Error: Cannot find module**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Error: Port 5173 already in use**
- The terminal will suggest an alternative port
- Or edit `frontend/vite.config.js` to change the port

### API Issues

**HeyGen API errors:**
- Verify your API key is correct
- Check your HeyGen account has available credits
- Ensure you're not rate-limited

**ElevenLabs API errors:**
- Verify your API key is correct
- Check you haven't exceeded your monthly character limit
- Try using the default voice ID first

## Usage

1. **Upload Images:** Drag and drop product images
2. **Product Details:** Enter product name and description
3. **Customize Avatar:** Choose an AI avatar and voice
4. **Generate:** Review and click "Generate Video"
5. **Wait:** Video generation takes 2-5 minutes
6. **Download:** Download your completed marketing video

## Cost Estimation

For a typical 30-second marketing video:

- **HeyGen:** ~$1.50 per video
- **ElevenLabs:** ~$0.10 per video (voiceover)
- **Total:** ~$1.60 per video

With free tiers, you can generate several test videos at no cost.

## Production Deployment

For production use, consider:

1. **Environment:**
   - Use `gunicorn` for the Flask backend
   - Build the frontend: `npm run build`
   - Serve via Nginx or similar

2. **Database:**
   - Replace in-memory job storage with Redis
   - Store video metadata in PostgreSQL

3. **Storage:**
   - Upload videos to AWS S3 or similar
   - Use CDN for video delivery

4. **Security:**
   - Use HTTPS
   - Implement authentication
   - Rate limiting
   - Input validation

## Support

If you encounter issues:

1. Check the console logs (both frontend and backend)
2. Verify API keys are correctly configured
3. Ensure all dependencies are installed
4. Check API service status pages

## Next Steps

- Customize avatar and voice options
- Add custom branding
- Implement user authentication
- Add video templates
- Integrate analytics

Enjoy creating amazing marketing videos with AI!
