# ⚡ START HERE - Quick Launch Guide

## 🚨 IMPORTANT: You Need API Keys First!

**Before the app will work, you MUST add your API keys to `backend\.env`**

### Get Your API Keys:

1. **HeyGen** (Required): https://app.heygen.com/ → Settings → API
2. **ElevenLabs** (Required): https://elevenlabs.io/ → Profile → API Key

### Add Keys to `.env`:

1. Open `backend\.env` in Notepad
2. Paste your keys:
   ```
   HEYGEN_API_KEY=your_actual_key_here
   ELEVENLABS_API_KEY=your_actual_key_here
   ```
3. Save the file

---

## 🚀 Start the Application

### Option 1: PowerShell (Recommended)

Right-click `run.ps1` → **Run with PowerShell**

### Option 2: Manual Start

**Terminal 1 - Backend:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python app.py
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

---

## 🌐 Open the App

Once both servers are running:

**Open your browser to:** http://localhost:5173

You should see the MarketAI interface!

---

## ❌ Troubleshooting

### "Nothing happens" when I open localhost:5173

**Check:**
1. Are both terminal windows running without errors?
2. Did you add your API keys to `backend\.env`?
3. Wait 10-15 seconds after starting for frontend to compile

### "Module not found" errors

**Backend:**
```powershell
cd backend
.\venv\Scripts\pip install -r requirements.txt
```

**Frontend:**
```powershell
cd frontend
npm install
```

### "Port already in use"

Something else is using port 5000 or 5173. Close other applications or restart your computer.

---

## ✅ Checklist

- [ ] Python and Node.js installed
- [ ] Ran `pip install -r requirements.txt` in backend
- [ ] Ran `npm install` in frontend
- [ ] Added HeyGen API key to `backend\.env`
- [ ] Added ElevenLabs API key to `backend\.env`
- [ ] Started backend server (Terminal 1)
- [ ] Started frontend server (Terminal 2)
- [ ] Opened http://localhost:5173 in browser

---

## 💡 Next Steps

Once running:
1. Upload a product image
2. Enter product details
3. Choose avatar & voice
4. Generate your first video!

**Each video costs ~$1.60 to generate** (free trial credits available)

---

Need detailed help? See [SETUP_GUIDE.md](SETUP_GUIDE.md)
