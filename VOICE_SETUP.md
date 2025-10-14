# Voice Assistant Setup Guide

## 🔒 HTTPS Requirement

**Important**: Voice recognition requires HTTPS or localhost for security reasons. The app currently shows an error because it's running on HTTP.

### Quick Fix for Development

**Option 1: Use localhost (Recommended for development)**
```bash
# Frontend
cd frontend
npm run dev -- --host localhost

# Backend  
cd backend
python app_api.py
```
Then access: `http://localhost:5173`

**Option 2: Enable HTTPS in development**
1. Install mkcert for local certificates:
```bash
# On macOS
brew install mkcert
mkcert -install

# Create certificates
cd frontend
mkcert localhost 127.0.0.1 ::1
```

2. Update `frontend/vite.config.js`:
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: 'localhost',
    https: {
      key: './localhost+2-key.pem',
      cert: './localhost+2.pem'
    }
  }
})
```

3. Start with HTTPS:
```bash
npm run dev
```
Then access: `https://localhost:5173`

## 🤖 OpenAI Setup (Optional)

To enable advanced AI voice processing:

1. Get an OpenAI API key from: https://platform.openai.com/api-keys
2. Set the environment variable:

### On macOS/Linux:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### On Windows:
```cmd
set OPENAI_API_KEY=your-api-key-here
```

### Or create a .env file in the backend directory:
```
OPENAI_API_KEY=your-api-key-here
```

## 🎤 Voice Features

The voice assistant supports the following commands:

### Habit Management
- **Add habits**: "Add a habit to drink water", "Create a habit for exercise"
- **Complete habits**: "Mark exercise as complete", "I did my reading"
- **Delete habits**: "Delete my water habit", "Remove the exercise habit"
- **Show habits**: "Show my habits", "List all my habits"
- **Check status**: "How am I doing with exercise?", "Status of my reading habit"

### UI Features
- **Single microphone button**: Click to expand the voice assistant panel
- **Web Speech API**: Browser-based voice recognition (requires HTTPS/localhost)
- **Text-to-Speech**: Spoken responses from Zelda
- **Fallback**: Manual text input if voice isn't supported
- **Real-time feedback**: Visual indicators for listening and processing

## 🔧 Troubleshooting

### "HTTPS Required" Error
- **Cause**: Voice recognition requires secure context
- **Fix**: Use localhost or enable HTTPS (see above)

### "Speech recognition error: network"
- **Cause**: Network connectivity issues
- **Fix**: Check internet connection and try again

### "Microphone access denied"
- **Cause**: Browser permissions not granted
- **Fix**: Click the microphone icon in the address bar and allow access

### Backend OpenAI Errors
- **Cause**: Missing or invalid OpenAI API key
- **Fix**: The app will fall back to pattern matching, which still works for basic commands

### Voice Not Working
- **Check**: Browser supports Web Speech API (Chrome, Edge, Safari)
- **Check**: Microphone permissions granted
- **Check**: Using HTTPS or localhost
- **Fallback**: Use the text input in the voice assistant panel

## 🚀 Quick Start

1. **Ensure HTTPS/localhost**: Use `http://localhost:5173` 
2. **Start both servers**:
   ```bash
   # Terminal 1 - Backend
   cd backend && python app_api.py
   
   # Terminal 2 - Frontend  
   cd frontend && npm run dev
   ```
3. **Test voice**: Click the microphone button, say "Add a habit to exercise"
4. **Verify**: Check that the habit appears in your habits list

The voice assistant will work with pattern matching even without OpenAI setup!
