# Quick Start Guide - Market AI

Get your professional product image generator running in 5 minutes!

## Step 1: Get Your API Key (2 minutes)

1. Go to https://replicate.com/
2. Click "Sign Up" (it's free!)
3. Verify your email
4. Go to https://replicate.com/account/api-tokens
5. Copy your API token (starts with `r8_...`)

## Step 2: Setup Backend (2 minutes)

Open terminal/command prompt:

```bash
# Navigate to backend folder
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file (Windows)
copy .env.example .env

# Or on Mac/Linux
cp .env.example .env
```

Now open the `.env` file and paste your API token:
```
REPLICATE_API_TOKEN=r8_your_token_here
```

## Step 3: Setup Frontend (1 minute)

Open a new terminal:

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install
```

## Step 4: Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Step 5: Generate Your First Image!

1. Open http://localhost:5173 in your browser
2. Type: "luxury smartwatch with black screen and leather strap"
3. Click "Generate Image"
4. Wait ~30 seconds
5. Download your professional marketing image!

## Troubleshooting

**Can't install Python packages?**
```bash
# Create a virtual environment first
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Then install
pip install -r requirements.txt
```

**API Token not working?**
- Make sure you copied the full token (starts with `r8_`)
- Check for extra spaces in the .env file
- Restart the Flask server after adding the token

**Port already in use?**
- Backend: Change port in app.py (last line)
- Frontend: It will auto-suggest a different port

## What's Next?

- Try different product descriptions
- Upload reference images for better results
- Experiment with style presets (Professional, Luxury, Modern, Vibrant)
- Generate multiple variations and pick the best one

## Cost

Each image costs ~$0.01 with Replicate. New accounts get $5 free credit = 500 free images!

Happy generating! 🎨
