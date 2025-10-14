import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Send, MessageCircle, X } from 'lucide-react';
import './VoiceAssistant.css';
import { validateToken, makeAuthenticatedRequest, handleAuthError } from '../utils/auth';

const VoiceAssistant = ({ onVoiceCommand }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState('');
  const [isExpanded, setIsExp              <div className="command-category">
                <p><strong>📅 Information:</strong></p>
                <ul>
                  <li>"What's today's schedule?"</li>
                  <li>"Show calendar"</li>
                  <li>"About this app"</li>
                </ul>
              </div>

              <div className="command-category">
                <p><strong>🧪 Test Mode:</strong></p>
                <ul>
                  <li>Type any command above and click Send to test</li>
                  <li>Try: "go to analytics" or "add habit to run"</li>
                  <li>This bypasses voice and tests the full system</li>
                </ul>
              </div>

              {useWhisper && (
                <div className="whisper-info">
                  <p><strong>🚀 Enhanced with Whisper-large:</strong></p>
                  <p>Accurate transcription with full app control!</p>
                  <p><strong>💡 Debug Tip:</strong> If voice transcription shows "Thank you", use text input to test commands!</p>
                  <p><strong>🔧 Quick Test:</strong> Type "go to analytics" and click Send button</p>
                </div>
              )}
            </div>(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [httpsRequired, setHttpsRequired] = useState(false);
  const [volume, setVolume] = useState(0);
  const [useWhisper, setUseWhisper] = useState(true); // Prefer Whisper-large over browser speech recognition
  
  const recognitionRef = useRef(null);
  const synthRef = useRef(null);
  const animationRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Initialize speech recognition and audio recording
  useEffect(() => {
    // Check if we're on HTTPS or localhost
    const isSecureContext = window.location.protocol === 'https:' || 
                           window.location.hostname === 'localhost' || 
                           window.location.hostname === '127.0.0.1';
    
    if (!isSecureContext) {
      setHttpsRequired(true);
      setSpeechSupported(false);
      return;
    }

    // Initialize MediaRecorder for Whisper-large audio processing
    if (navigator.mediaDevices && MediaRecorder.isTypeSupported('audio/webm')) {
      console.log('✅ MediaRecorder supported for Whisper audio processing');
    } else {
      console.warn('⚠️ MediaRecorder not fully supported, falling back to browser speech recognition');
      setUseWhisper(false);
    }

    // Initialize browser speech recognition as fallback
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      const recognition = recognitionRef.current;
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        startVolumeAnimation();
      };

      recognition.onresult = (event) => {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          currentTranscript += event.results[i][0].transcript;
        }
        setTranscript(currentTranscript);
      };

      recognition.onend = () => {
        setIsListening(false);
        stopVolumeAnimation();
        if (transcript.trim()) {
          processVoiceCommand(transcript);
        }
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        stopVolumeAnimation();
        
        let errorMessage = '';
        switch (event.error) {
          case 'network':
            errorMessage = 'Network error - please make sure you have internet connection.';
            break;
          case 'not-allowed':
            errorMessage = 'Microphone access denied. Please allow microphone permissions and try again.';
            break;
          case 'no-speech':
            errorMessage = 'No speech detected. Please try speaking again.';
            break;
          case 'aborted':
            errorMessage = 'Speech recognition was cancelled.';
            break;
          case 'audio-capture':
            errorMessage = 'Audio capture failed. Please check your microphone.';
            break;
          case 'service-not-allowed':
            errorMessage = 'Speech service not allowed. Please use HTTPS or localhost.';
            break;
          default:
            errorMessage = `Speech recognition error: ${event.error}. Please try again or use text input.`;
        }
        
        setResponse(errorMessage);
      };
    } else {
      setSpeechSupported(false);
    }

    // Initialize speech synthesis
    if ('speechSynthesis' in window) {
      synthRef.current = window.speechSynthesis;
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      stopVolumeAnimation();
    };
  }, [transcript]);

  // Simulate volume animation during listening
  const startVolumeAnimation = () => {
    const animate = () => {
      setVolume(Math.random() * 100);
      animationRef.current = requestAnimationFrame(animate);
    };
    animationRef.current = requestAnimationFrame(animate);
  };

  const stopVolumeAnimation = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    setVolume(0);
  };

  // Start voice recognition
  const startListening = () => {
    if (!speechSupported) {
      if (httpsRequired) {
        setResponse('Voice recognition requires HTTPS. Please use a secure connection or localhost.');
      } else {
        setResponse('Voice recognition is not supported in your browser.');
      }
      return;
    }

    if (isListening) return;

    setTranscript('');
    setResponse('');

    if (useWhisper) {
      // Use Whisper-large audio recording
      startWhisperRecording();
    } else {
      // Fallback to browser speech recognition
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch (error) {
          console.error('Failed to start speech recognition:', error);
          setResponse('Failed to start voice recognition. Please try again.');
        }
      }
    }
  };

  // Start Whisper-large audio recording
  const startWhisperRecording = async () => {
    try {
      console.log('🎤 Starting Whisper audio recording...');
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      });

      console.log('🎧 Microphone access granted, stream active:', stream.active);
      console.log('🎚️ Audio tracks:', stream.getAudioTracks().map(track => ({
        label: track.label,
        enabled: track.enabled,
        readyState: track.readyState
      })));

      const options = { mimeType: 'audio/webm;codecs=opus' };
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      mediaRecorderRef.current.addEventListener('dataavailable', (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      });

      mediaRecorderRef.current.addEventListener('stop', async () => {
        console.log('🎤 Audio recording stopped, processing with Whisper...');
        
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        console.log('📊 Audio blob created:', {
          size: audioBlob.size,
          type: audioBlob.type,
          chunks: audioChunksRef.current.length
        });
        
        // Stop all audio tracks
        stream.getTracks().forEach(track => track.stop());
        
        // Process with Whisper-large
        await processAudioCommand(audioBlob);
      });

      // Start recording
      mediaRecorderRef.current.start();
      setIsListening(true);
      startVolumeAnimation();
      
      console.log('✅ Whisper recording started');

    } catch (error) {
      console.error('Failed to start Whisper recording:', error);
      setResponse('Failed to access microphone. Please check permissions and try again.');
    }
  };

  // Stop voice recognition
  const stopListening = () => {
    if (useWhisper && mediaRecorderRef.current) {
      if (mediaRecorderRef.current.state === 'recording') {
        console.log('🛑 Stopping Whisper recording...');
        mediaRecorderRef.current.stop();
      }
    } else if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
    }
    
    setIsListening(false);
    stopVolumeAnimation();
  };

  // Process voice command
  const processVoiceCommand = async (command) => {
    if (!command.trim()) return;

    setIsProcessing(true);
    setResponse('Processing your request...');

    try {
      // Use the unified chat endpoint for text processing with auth utilities
      const response = await makeAuthenticatedRequest('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: command })
      });

      const data = await response.json();
      
      if (response.ok) {
        const reply = data.reply || 'Command processed successfully';
        setResponse(reply);
        
        // Call parent callback if provided
        if (onVoiceCommand) {
          onVoiceCommand({
            ...data,
            transcript: command,
            source: 'voice_text'
          });
        }

        // Speak the response if speech synthesis is available
        speakResponse(reply);
      } else {
        setResponse(data.error || 'Sorry, I couldn\'t process that request.');
      }
    } catch (error) {
      console.error('Voice command processing error:', error);
      setResponse('Sorry, there was an error processing your request.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Process audio using Whisper-large
  const processAudioCommand = async (audioBlob) => {
    try {
      setIsProcessing(true);
      setTranscript('Processing audio...');

      // Use the utility function for token validation
      const token = localStorage.getItem('token');
      const validation = validateToken(token);
      
      if (!validation.valid) {
        setResponse(`Authentication error: ${validation.reason}`);
        setTranscript('Please login again');
        
        if (validation.reason === 'Token expired') {
          localStorage.removeItem('token');
        }
        return;
      }

      console.log('✅ Token validation passed for user:', validation.payload.user_id);

      // Create form data
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      console.log('🎤 Sending audio to server...');

      // Use the utility function for authenticated requests
  const response = await makeAuthenticatedRequest('/api/voice', {
        method: 'POST',
        body: formData,
      });

      console.log('📡 Response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Server error:', errorData);
        throw new Error(`HTTP ${response.status}: ${errorData.error || 'Unknown error'}`);
      }

      const data = await response.json();
      console.log('✅ Voice processing successful:', data);

      // Update UI with results
      setTranscript(data.transcript || 'Voice processed successfully');
      setResponse(data.reply || 'Command processed');

      // Speak the response
      if (data.reply) {
        speakResponse(data.reply);
      }

      // Handle habit actions
      if (data.action_taken && data.habit_action) {
        console.log('🎯 Habit action taken:', data.habit_action);
        if (onVoiceCommand) {
          onVoiceCommand(data);
        }
      }

    } catch (error) {
      handleAuthError(error, setResponse, setTranscript);
    } finally {
      setIsProcessing(false);
    }
  };

  // Text-to-speech response
  const speakResponse = (text) => {
    if (synthRef.current && text) {
      // Cancel any ongoing speech
      synthRef.current.cancel();
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 0.8;
      
      synthRef.current.speak(utterance);
    }
  };

  // Handle manual text input
  const handleManualSubmit = () => {
    if (transcript.trim() && !isProcessing) {
      processVoiceCommand(transcript);
    }
  };

  // Handle text input change
  const handleTextChange = (e) => {
    setTranscript(e.target.value);
  };

  // Toggle voice assistant panel
  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  if (!speechSupported) {
    return (
      <div className="voice-assistant voice-assistant-error">
        <div className="voice-error-message">
          <Mic size={24} />
          <div>
            {httpsRequired ? (
              <div>
                <p><strong>HTTPS Required</strong></p>
                <p>Voice recognition requires a secure connection. Please:</p>
                <ul>
                  <li>Use HTTPS (https://your-domain.com)</li>
                  <li>Or access via localhost for development</li>
                </ul>
              </div>
            ) : (
              <span>Voice recognition not supported in this browser</span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`voice-assistant ${isExpanded ? 'expanded' : ''}`}>
      {/* Voice Assistant Toggle Button */}
      <button 
        className={`voice-toggle ${isListening ? 'listening' : ''} ${isProcessing ? 'processing' : ''}`}
        onClick={toggleExpanded}
        title="Voice Assistant"
      >
        <Mic size={20} />
        {isListening && (
          <div className="volume-indicator">
            <div 
              className="volume-bar" 
              style={{ height: `${Math.max(10, volume)}%` }}
            ></div>
          </div>
        )}
      </button>

      {/* Expanded Voice Assistant Panel */}
      {isExpanded && (
        <div className="voice-panel">
          <div className="voice-header">
            <h3>Voice Assistant</h3>
            <button 
              className="close-btn" 
              onClick={toggleExpanded}
              title="Close"
            >
              <X size={16} />
            </button>
          </div>

          <div className="voice-content">
            {/* Status Display */}
            <div className="voice-status">
              {isListening && (
                <div className="listening-indicator">
                  <div className="pulse"></div>
                  <span>Listening...</span>
                </div>
              )}
              {isProcessing && (
                <div className="processing-indicator">
                  <div className="spinner"></div>
                  <span>Processing...</span>
                </div>
              )}
            </div>

            {/* Text Input Area */}
            <div className="voice-input">
              <textarea
                value={transcript}
                onChange={handleTextChange}
                placeholder="Say something or type your command here..."
                className="voice-textarea"
                rows="3"
                disabled={isListening || isProcessing}
              />
              
              <div className="voice-controls">
                <button
                  className={`mic-btn ${isListening ? 'listening' : ''}`}
                  onClick={isListening ? stopListening : startListening}
                  disabled={isProcessing}
                  title={isListening ? 'Stop listening' : 'Start listening'}
                >
                  {isListening ? <MicOff size={20} /> : <Mic size={20} />}
                </button>
                
                <button
                  className="send-btn"
                  onClick={handleManualSubmit}
                  disabled={!transcript.trim() || isProcessing || isListening}
                  title="Send command"
                >
                  <Send size={20} />
                </button>
              </div>
            </div>

            {/* Response Area */}
            {response && (
              <div className="voice-response">
                <h4>Response:</h4>
                <p>{response}</p>
              </div>
            )}

            {/* Help Text */}
            <div className="voice-help">
              <p><strong>🎤 Complete Voice Commands Available:</strong></p>
              
              <div className="command-category">
                <p><strong>🏠 Navigation:</strong></p>
                <ul>
                  <li>"Go to home" / "Take me home"</li>
                  <li>"Open habits" / "Show my habits"</li>
                  <li>"Go to analytics" / "Show stats"</li>
                  <li>"Open chat" / "Start conversation"</li>
                  <li>"Go to settings"</li>
                </ul>
              </div>

              <div className="command-category">
                <p><strong>🎯 Habit Management:</strong></p>
                <ul>
                  <li>"Add a habit to drink water"</li>
                  <li>"Create a habit to exercise daily"</li>
                  <li>"Mark exercise as complete"</li>
                  <li>"Delete my reading habit"</li>
                  <li>"How am I doing with meditation?"</li>
                </ul>
              </div>

              <div className="command-category">
                <p><strong>⚙️ App Controls:</strong></p>
                <ul>
                  <li>"Refresh page" / "Update data"</li>
                  <li>"Log out" / "Sign out"</li>
                  <li>"Show account" / "View profile"</li>
                  <li>"Help" / "What can I do?"</li>
                </ul>
              </div>

              <div className="command-category">
                <p><strong>📅 Information:</strong></p>
                <ul>
                  <li>"What's today's schedule?"</li>
                  <li>"Show calendar"</li>
                  <li>"About this app"</li>
                </ul>
              </div>

              {useWhisper && (
                <div className="whisper-info">
                  <p><strong>🚀 Enhanced with Whisper-large:</strong></p>
                  <p>Accurate transcription with full app control!</p>
                  <p><strong>� Tip:</strong> Speak naturally - I understand context and can control the entire app!</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceAssistant;
