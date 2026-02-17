# Market AI - Professional Product Image Generator

A simple, focused AI tool that generates professional marketing-ready product images using Stable Diffusion XL (SDXL).

## Features

- 🎨 Generate high-quality product images from descriptions
- 🖼️ Optional reference image support (img2img)
- ✨ Multiple style presets (Professional, Luxury, Modern, Vibrant)
- 📸 Marketing-ready outputs optimized for ads and e-commerce
- 💾 Direct download of generated images
- 🚀 Simple, clean interface

## Tech Stack

**Backend:**
- Python 3.9+
- Flask
- Replicate API (SDXL)
- Pillow for image processing

**Frontend:**
- React 18
- Vite
- Tailwind CSS
- Lucide React icons

## Prerequisites

You'll need a Replicate API token:

1. **Replicate** - https://replicate.com/
   - Sign up for a free account
   - Get your API token from https://replicate.com/account/api-tokens
   - Cost: ~$0.01 per image generation

## Installation

### 1. Clone and Setup Backend

```bash
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
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend` directory:

```env
REPLICATE_API_TOKEN=your_replicate_api_token_here
FLASK_ENV=development
FLASK_DEBUG=True
```

**To get your Replicate API token:**
1. Visit https://replicate.com/account/api-tokens
2. Copy your token
3. Paste it in the `.env` file

### 3. Setup Frontend

```bash
cd frontend
npm install
```

## Running the Application

### Start Backend Server

```bash
cd backend
venv\Scripts\activate  # or source venv/bin/activate on Mac/Linux
python app.py
```

Backend will run on `http://localhost:5000`

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

Frontend will run on `http://localhost:5173`

## Usage

1. Open `http://localhost:5173` in your browser
2. Enter a product description (e.g., "luxury wristwatch with silver band and blue dial")
3. Choose a style preset (Professional, Luxury, Modern, or Vibrant)
4. Optionally upload a reference product image
5. Click "Generate Image"
6. Wait for the AI to generate your image (~30-60 seconds)
7. Download your professional marketing image

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/upload-image` - Upload reference image (optional)
- `POST /api/generate-image` - Generate marketing image
- `GET /api/status/:job_id` - Check generation status
- `GET /api/image/:job_id` - Get generated image
- `GET /api/download/:job_id` - Download generated image

## Example Prompts

- "luxury smartwatch with black screen and leather strap"
- "wireless earbuds in charging case, white color"
- "perfume bottle with golden cap on marble surface"
- "running shoes with red and white design"
- "laptop with thin bezels and metallic finish"

## Tips for Best Results

1. **Be Specific**: Include details about color, material, style
2. **Use Reference Images**: Upload a product photo for better accuracy
3. **Try Different Styles**: Each style preset creates a different aesthetic
4. **Iterate**: Generate multiple images and pick the best one

## Cost Considerations

- **Replicate (SDXL)**: ~$0.01 per image
- Free tier available with $5 credit for new accounts
- Very affordable for testing and small-scale production

## Troubleshooting

**"REPLICATE_API_TOKEN not configured"**
- Make sure you created the `.env` file in the `backend` directory
- Check that your API token is correctly pasted
- Restart the Flask server after adding the token

**Images taking too long**
- SDXL generation typically takes 30-60 seconds
- Check your internet connection
- Verify Replicate API status at https://replicate.com/status

**Generated images don't match description**
- Try being more specific in your description
- Use a reference image for better guidance
- Experiment with different style presets

## License

MIT
