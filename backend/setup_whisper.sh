#!/bin/bash

# Zelda AI Assistant - Whisper-large Integration Setup Script
# This script sets up the complete voice-to-chat pipeline with Whisper-large

echo "🧚‍♀️ Setting up Zelda AI Assistant with Whisper-large integration..."
echo "================================================================="

# Check if we're in the backend directory
if [ ! -f "app_api.py" ]; then
    echo "❌ Please run this script from the backend directory"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8 or higher is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install PyTorch with appropriate version for the system
echo "🔥 Installing PyTorch..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if [[ $(uname -m) == "arm64" ]]; then
        # Apple Silicon
        echo "🍎 Detected Apple Silicon, installing optimized PyTorch..."
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    else
        # Intel Mac
        echo "🍎 Detected Intel Mac, installing PyTorch..."
        pip install torch torchaudio
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "🐧 Detected Linux, installing PyTorch..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
else
    # Windows/WSL or other
    echo "🖥️ Installing PyTorch with CPU support..."
    pip install torch torchaudio
fi

# Install Whisper and other dependencies
echo "🎤 Installing Whisper-large and dependencies..."
pip install openai-whisper

# Install the remaining requirements
echo "📋 Installing remaining dependencies..."
pip install -r requirements-whisper.txt

# Test Whisper installation
echo "🧪 Testing Whisper installation..."
python3 -c "
import whisper
print('✅ Whisper imported successfully')
try:
    model = whisper.load_model('base')
    print('✅ Whisper base model loaded successfully')
    print('🎯 Whisper-large will be downloaded on first use')
except Exception as e:
    print(f'⚠️ Warning: {e}')
    print('Whisper models will be downloaded when first used')
"

# Test other imports
echo "🔍 Testing other imports..."
python3 -c "
try:
    from intent_parser import parse_user_intent
    print('✅ Intent parser imported successfully')
except ImportError as e:
    print(f'❌ Intent parser import failed: {e}')

try:
    from habit_automation import execute_habit_action
    print('✅ Habit automation imported successfully')
except ImportError as e:
    print(f'❌ Habit automation import failed: {e}')

try:
    from whisper_service import transcribe_audio_bytes
    print('✅ Whisper service imported successfully')
except ImportError as e:
    print(f'❌ Whisper service import failed: {e}')
"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🚀 To start the enhanced Zelda AI Assistant:"
echo "   1. Make sure you're in the backend directory"
echo "   2. Activate the virtual environment: source venv/bin/activate"
echo "   3. Start the server: python app_api.py"
echo ""
echo "✨ New Features Available:"
echo "   • Whisper-large speech-to-text transcription"
echo "   • Intelligent habit action detection"
echo "   • Unified voice and text chat pipeline"
echo "   • Automatic habit database updates"
echo "   • Enhanced natural language understanding"
echo ""
echo "🎤 Voice Commands Supported:"
echo "   • 'Add a habit to drink water'"
echo "   • 'Mark exercise as complete'"
echo "   • 'Mark meditation as done on September 20th'"
echo "   • 'Delete my reading habit'"
echo "   • 'Show my habits'"
echo "   • 'Rename exercise to morning workout'"
echo "   • Plus normal conversation!"
echo ""
echo "🔧 Frontend Setup:"
echo "   • The React frontend will automatically use the new voice features"
echo "   • Make sure to run from localhost (http://localhost:5173) for voice permissions"
echo ""
echo "📊 Note: The first time you use voice, Whisper-large (~3GB) will be downloaded"