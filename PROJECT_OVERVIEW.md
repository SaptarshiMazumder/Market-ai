# MarketAI - Project Overview

A professional AI-powered video generation pipeline for creating high-quality product marketing videos with realistic human avatars.

## What This Does

Transform product images and descriptions into professional marketing videos featuring:
- Realistic AI avatars presenting your product
- Professional voiceovers in multiple voices
- Clean, production-ready output
- Quick 2-5 minute generation time

## Architecture

```
MarketAI/
├── backend/              # Python Flask API
│   ├── app.py           # Main Flask application
│   ├── config.py        # Configuration and API keys
│   ├── services/
│   │   ├── video_generator.py    # Video generation pipeline
│   │   └── image_processor.py    # Image preprocessing
│   ├── uploads/         # Uploaded product images
│   └── generated/       # Generated videos
│
├── frontend/            # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/  # React components
│   │   │   ├── Header.jsx
│   │   │   ├── VideoGenerator.jsx
│   │   │   ├── ImageUpload.jsx
│   │   │   ├── ProductDetails.jsx
│   │   │   ├── AvatarSelector.jsx
│   │   │   ├── GenerationProgress.jsx
│   │   │   └── VideoPreview.jsx
│   │   ├── services/
│   │   │   └── api.js   # API client
│   │   ├── App.jsx      # Main app component
│   │   └── index.css    # Tailwind styles
│   └── public/
│
└── docs/
    ├── README.md        # Main documentation
    ├── QUICKSTART.md    # 5-minute setup guide
    ├── SETUP_GUIDE.md   # Detailed setup instructions
    └── API_KEYS.md      # How to get API keys
```

## Tech Stack

### Backend
- **Flask** - Lightweight Python web framework
- **HeyGen API** - AI avatar video generation
- **ElevenLabs API** - Professional voiceover generation
- **RunwayML API** - Optional video enhancement
- **OpenCV** - Image processing and enhancement
- **Pillow** - Image manipulation

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Lucide React** - Icon library
- **React Dropzone** - File upload
- **Axios** - HTTP client

## Features

### Current Features
✅ Multi-image upload with drag & drop
✅ Automatic image preprocessing and enhancement
✅ AI script generation based on product description
✅ Custom script support
✅ Multiple video styles (professional, casual, energetic)
✅ Avatar selection
✅ Voice selection
✅ Real-time generation progress tracking
✅ Video download
✅ Clean, modern UI

### Planned Features
🔄 User authentication
🔄 Video templates
🔄 Multiple output formats
🔄 Video editing capabilities
🔄 Batch processing
🔄 Analytics dashboard
🔄 Custom branding
🔄 Integration with social media platforms

## API Integration

### HeyGen API
- **Purpose:** Generate realistic avatar videos
- **Endpoint:** `https://api.heygen.com/v2`
- **Features Used:**
  - Avatar video generation
  - Multiple avatar options
  - HD video output (1920x1080)
  - Voice integration

### ElevenLabs API
- **Purpose:** Professional voiceover generation
- **Endpoint:** `https://api.elevenlabs.io/v1`
- **Features Used:**
  - Text-to-speech conversion
  - Multiple voice options
  - Natural voice modulation
  - Multi-lingual support

### RunwayML API (Optional)
- **Purpose:** Additional video enhancement
- **Endpoint:** `https://api.runwayml.com/v1`
- **Features Used:**
  - Gen-3 video generation
  - Product visual enhancement

## Workflow

1. **Image Upload**
   - User uploads product images
   - Images are processed and enhanced
   - Thumbnails generated for preview

2. **Product Details**
   - User enters product name and description
   - Choose video style
   - Optional custom script

3. **Avatar Customization**
   - Select AI avatar
   - Choose voice
   - Preview options

4. **Generation**
   - Script generation (if not provided)
   - Voiceover generation with ElevenLabs
   - Avatar video generation with HeyGen
   - Optional enhancement with RunwayML
   - Progress tracking in real-time

5. **Download**
   - Video ready for download
   - Production-ready MP4 format
   - Full HD quality (1920x1080)

## Performance

- **Average Generation Time:** 2-5 minutes
- **Video Quality:** Full HD (1920x1080)
- **Supported Image Formats:** PNG, JPG, JPEG, WEBP
- **Max Upload Size:** 50MB per image
- **Concurrent Jobs:** 1 (expandable with task queue)

## Scalability Considerations

### Current Setup (Development)
- In-memory job tracking
- Local file storage
- Single worker process

### Production Recommendations
- **Job Queue:** Celery + Redis for background tasks
- **Database:** PostgreSQL for job metadata
- **Storage:** AWS S3 or similar for videos/images
- **CDN:** CloudFront for video delivery
- **Load Balancer:** Nginx for multiple workers
- **Monitoring:** Sentry for error tracking
- **Analytics:** Track generation metrics

## Cost Analysis

Per video (30-second marketing video):
- **HeyGen:** ~$1.50
- **ElevenLabs:** ~$0.10
- **Total:** ~$1.60

Monthly estimates (100 videos):
- **HeyGen:** ~$150
- **ElevenLabs:** ~$10
- **Infrastructure:** ~$20 (hosting)
- **Total:** ~$180/month

Free tier testing:
- 2-5 free videos using trial credits

## Security

Current implementation includes:
- File type validation
- File size limits
- Secure filename handling
- CORS configuration
- API key environment variables

Production recommendations:
- User authentication (JWT)
- Rate limiting
- Input sanitization
- HTTPS only
- API key rotation
- Video access control
- Audit logging

## Development

### Running Locally

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py

# Frontend
cd frontend
npm install
npm run dev
```

### Environment Variables

Required in `backend/.env`:
```env
HEYGEN_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
RUNWAYML_API_KEY=your_key  # Optional
```

### API Endpoints

- `GET /api/health` - Health check
- `POST /api/upload-images` - Upload product images
- `POST /api/generate-video` - Start video generation
- `GET /api/status/:job_id` - Check generation status
- `GET /api/download/:job_id` - Download video
- `GET /api/avatars` - List available avatars
- `GET /api/voices` - List available voices

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Opera (latest)

## Known Limitations

1. **Single Job Processing:** Currently processes one video at a time
2. **No Authentication:** Anyone with access can generate videos
3. **Local Storage:** Videos stored locally (not cloud)
4. **No Video Editing:** Generated videos can't be edited in-app
5. **Limited Customization:** Fixed video format and dimensions

## Future Enhancements

1. **User System**
   - Authentication and authorization
   - User dashboards
   - Usage tracking and quotas

2. **Advanced Features**
   - Video templates
   - Custom branding overlays
   - Background music
   - Multiple video formats
   - Batch processing

3. **Integration**
   - Social media auto-posting
   - CMS integration
   - E-commerce platform plugins
   - Webhook notifications

4. **Analytics**
   - Generation metrics
   - Cost tracking
   - Performance monitoring
   - User analytics

## License

MIT License - Feel free to use and modify for your needs.

## Support

For issues or questions:
1. Check documentation in `/docs`
2. Review console logs for errors
3. Verify API keys are correctly configured
4. Check API service status pages

## Acknowledgments

Built with:
- [HeyGen](https://heygen.com) - AI Avatar Technology
- [ElevenLabs](https://elevenlabs.io) - AI Voice Technology
- [RunwayML](https://runwayml.com) - AI Video Enhancement
- [React](https://react.dev) - UI Framework
- [Tailwind CSS](https://tailwindcss.com) - Styling
- [Flask](https://flask.palletsprojects.com) - Backend Framework

---

**Happy Video Creating! 🎥✨**
