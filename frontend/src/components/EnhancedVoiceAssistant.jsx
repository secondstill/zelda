import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Send, MessageCircle, X, Volume2 } from 'lucide-react';
import './VoiceAssistant.css';
import { validateToken, makeAuthenticatedRequest, handleAuthError } from '../utils/auth';

const EnhancedVoiceAssistant = ({ onVoiceCommand }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [volume, setVolume] = useState(0);
  const [isVADActive, setIsVADActive] = useState(false);
  
  const recognitionRef = useRef(null);
  const synthRef = useRef(null);
  const animationRef = useRef(null);
  const vadRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const microphoneRef = useRef(null);
  const vadTimeoutRef = useRef(null);
  const speechTimeoutRef = useRef(null);

  // Initialize enhanced speech recognition
  useEffect(() => {
    console.log('🔧 Initializing Enhanced Voice Assistant');
    
    try {
      // Initialize Speech Recognition
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognitionRef.current = new SpeechRecognition();
        
        const recognition = recognitionRef.current;
        recognition.continuous = true;   // Try continuous mode for better capture
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;  // Simplified for debugging
        
        // Add service hints for better audio capture
        if (recognition.serviceURI !== undefined) {
          console.log('🎤 Speech recognition service available');
        }
        
        // Remove grammar list - it may interfere with speech recognition
        // Focus on basic speech recognition first
        
        recognition.onstart = () => {
          console.log('🎤 SPEECH: Speech recognition started successfully');
          console.log('🎤 SPEECH: Recognition settings - continuous:', recognition.continuous, 'lang:', recognition.lang);
          setIsListening(true);
          
          // Set a timeout to process any captured speech after 10 seconds (longer time)
          speechTimeoutRef.current = setTimeout(() => {
            console.log('⏰ SPEECH: Timeout reached, checking for transcript');
            if (transcript.trim()) {
              console.log('⏰ SPEECH: Processing transcript from timeout:', transcript.trim());
              processVoiceCommandImmediate(transcript.trim());
            } else {
              console.log('⏰ SPEECH: No transcript captured after timeout');
              console.log('⏰ SPEECH: This might indicate microphone or browser speech recognition issues');
              setResponse('No speech detected. Try speaking louder or check microphone settings.');
            }
          }, 10000);
        };

        recognition.onresult = (event) => {
          console.log('🎤 SPEECH: onresult triggered, event.results.length:', event.results.length);
          console.log('🎤 SPEECH: Full event details:', {
            resultIndex: event.resultIndex,
            results: Array.from(event.results).map((result, i) => ({
              index: i,
              isFinal: result.isFinal,
              transcript: result[0].transcript,
              confidence: result[0].confidence
            }))
          });
          
          let interimTranscript = '';
          let finalTranscript = '';
          
          // Process all results, not just from resultIndex
          for (let i = 0; i < event.results.length; i++) {
            const result = event.results[i];
            const transcript = result[0].transcript;
            console.log(`🎤 SPEECH: Result ${i} - isFinal:`, result.isFinal, 'transcript:', `"${transcript}"`, 'confidence:', result[0].confidence);
            
            if (result.isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }
          
          const currentTranscript = finalTranscript || interimTranscript;
          console.log('🎤 SPEECH: Setting transcript to:', `"${currentTranscript}"`);
          setTranscript(currentTranscript);
          
          // Process any transcript we get, even if not marked as final
          if (currentTranscript.trim()) {
            console.log('🎙️ SPEECH: Transcript captured:', `"${currentTranscript.trim()}"`, 'isFinal:', finalTranscript.length > 0);
            
            // For continuous mode, process interim results after a delay
            if (!finalTranscript && interimTranscript.trim()) {
              console.log('🎙️ SPEECH: Got interim result, will process if no final result comes');
              // Don't process interim immediately, wait for final or timeout
            } else if (finalTranscript.trim()) {
              console.log('🎙️ SPEECH: Processing final transcript immediately');
              // Clear the timeout since we got final results
              if (speechTimeoutRef.current) {
                clearTimeout(speechTimeoutRef.current);
                speechTimeoutRef.current = null;
              }
              processVoiceCommandImmediate(finalTranscript.trim());
            }
          } else {
            console.log('🎙️ SPEECH: No usable transcript in this result');
          }
        };

        recognition.onend = () => {
          console.log('🎤 SPEECH: Speech recognition ended');
          console.log('🎤 SPEECH: Current transcript when ended:', `"${transcript}"`);
          setIsListening(false);
          
          // Clear the timeout
          if (speechTimeoutRef.current) {
            clearTimeout(speechTimeoutRef.current);
            speechTimeoutRef.current = null;
          }
          
          // Stop VAD monitoring and close audio context to release microphone
          if (vadRef.current) {
            cancelAnimationFrame(vadRef.current);
            vadRef.current = null;
          }
          if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
          }
          console.log('🔊 VAD cleaned up automatically after speech recognition ended');
          
          // Process any transcript we have, even if it wasn't marked as final
          if (transcript.trim() && transcript.trim().length > 1) {
            console.log('🎤 SPEECH: Processing transcript from onend (may be interim):', transcript.trim());
            processVoiceCommandImmediate(transcript.trim());
          } else {
            console.log('🎤 SPEECH: No usable transcript captured');
            setResponse('No speech captured. Please try speaking more clearly or check microphone.');
          }
          
          console.log('🎤 SPEECH: Recognition ended, microphone released, ready for next command');
        };

        recognition.onerror = (event) => {
          console.error('❌ Speech recognition error:', event.error);
          if (event.error === 'no-speech') {
            console.log('💡 No speech detected, continuing to listen...');
            // Don't show error for no-speech, just continue
            return;
          }
          setResponse(`Speech error: ${event.error}. Try again.`);
        };
      } else {
        console.log('❌ Speech Recognition not supported');
        setSpeechSupported(false);
      }

      // Initialize Speech Synthesis
      if ('speechSynthesis' in window) {
        synthRef.current = window.speechSynthesis;
      }

      // Don't initialize VAD automatically - only when user starts recording

    } catch (error) {
      console.error('❌ Error initializing Enhanced Voice Assistant:', error);
      setSpeechSupported(false);
    }

    return () => {
      cleanup();
    };
  }, []);

  // Initialize Voice Activity Detection
  const initializeVAD = async () => {
    try {
      console.log('🔊 Initializing Voice Activity Detection');
      
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log('❌ MediaDevices not supported');
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
          channelCount: 1
        } 
      });

      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      microphoneRef.current = audioContextRef.current.createMediaStreamSource(stream);
      
      analyserRef.current.fftSize = 512;
      analyserRef.current.smoothingTimeConstant = 0.8;
      microphoneRef.current.connect(analyserRef.current);
      
      console.log('✅ VAD initialized successfully');
      
    } catch (error) {
      console.error('❌ VAD initialization failed:', error);
      setResponse('Microphone access required for voice commands. Please allow permissions.');
    }
  };

  // Voice Activity Detection loop
  const startVADMonitoring = useCallback(() => {
    if (!analyserRef.current) return;
    
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const checkVAD = () => {
      if (!analyserRef.current) return;
      
      analyserRef.current.getByteFrequencyData(dataArray);
      
      // Calculate volume level
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      
      // Log audio levels occasionally for debugging
      if (Math.random() < 0.01) { // 1% chance to log
        console.log('🔊 Audio monitoring - sum:', sum, 'bufferLength:', bufferLength, 'average:', sum / bufferLength);
      }
      const averageVolume = sum / bufferLength;
      setVolume(averageVolume);
      
      // Voice activity detection threshold
      const vadThreshold = 25;
      const isVoiceActive = averageVolume > vadThreshold;
      
      if (isVoiceActive && !isVADActive) {
        console.log('🗣️ Voice activity detected!');
        setIsVADActive(true);
        startSpeechRecognition();
        
        // Clear any existing timeout
        if (vadTimeoutRef.current) {
          clearTimeout(vadTimeoutRef.current);
        }
      } else if (isVoiceActive && isVADActive) {
        // Reset timeout if voice is still active
        if (vadTimeoutRef.current) {
          clearTimeout(vadTimeoutRef.current);
        }
        
        vadTimeoutRef.current = setTimeout(() => {
          console.log('🔇 Voice activity stopped');
          setIsVADActive(false);
          stopSpeechRecognition();
        }, 2000); // 2 second silence threshold
      }
      
      if (isListening || isVADActive) {
        vadRef.current = requestAnimationFrame(checkVAD);
      }
    };
    
    vadRef.current = requestAnimationFrame(checkVAD);
  }, [isVADActive, isListening]);

  // Start speech recognition
  const startSpeechRecognition = async () => {
    if (!recognitionRef.current || isListening) return;
    
    try {
      console.log('🎤 Starting speech recognition');
      
      // Initialize VAD only when starting to record
      if (!audioContextRef.current) {
        console.log('🔊 Initializing VAD for recording session...');
        await initializeVAD();
      }
      
      // Check microphone permissions
      try {
        console.log('🎤 Checking microphone permissions...');
        
        // Use default microphone with basic constraints
        const audioConstraints = { 
          echoCancellation: false, 
          noiseSuppression: false 
        };
          
        console.log('🎤 Using audio constraints:', audioConstraints);
        const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        console.log('🎤 Microphone access granted, audio tracks:', stream.getAudioTracks().length);
        
        // Test if we're actually getting audio
        const track = stream.getAudioTracks()[0];
        if (track) {
          console.log('🎤 Audio track details:', {
            enabled: track.enabled,
            muted: track.muted,
            readyState: track.readyState,
            label: track.label
          });
          
          // Warn if using BlackHole or virtual device
          if (track.label.includes('BlackHole') || track.label.includes('Virtual')) {
            console.warn('⚠️ Using virtual audio device! This may not capture your voice.');
            setResponse('Warning: Using virtual audio device. Please select your real microphone.');
          }
        }
        
        // Stop the stream since we just needed to check permissions
        stream.getTracks().forEach(track => track.stop());
        console.log('🎤 Permission check complete, starting recognition...');
      } catch (permError) {
        console.error('🎤 Microphone permission error:', permError);
        setResponse('Microphone permission denied. Please allow microphone access.');
        return;
      }
      
      setTranscript('');
      recognitionRef.current.start();
      
      // Start VAD monitoring only when recording
      startVADMonitoring();
      
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
    }
  };

  // Stop speech recognition and clean up VAD
  const stopSpeechRecognition = () => {
    if (recognitionRef.current && isListening) {
      console.log('🛑 Stopping speech recognition');
      recognitionRef.current.stop();
      
      // Stop VAD monitoring and close audio context to release microphone
      if (vadRef.current) {
        cancelAnimationFrame(vadRef.current);
        vadRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      console.log('🔊 VAD cleaned up, microphone released');
    }
  };



  // Process voice command immediately when detected
  const processVoiceCommandImmediate = async (command) => {
    console.log('🔍 STEP 1: processVoiceCommandImmediate called with command:', `"${command}"`);
    console.log('🔍 STEP 1: Command length:', command?.length);
    console.log('🔍 STEP 1: Command trimmed length:', command?.trim()?.length);
    
    if (!command || command.trim().length < 2) {
      console.log('❌ STEP 1: Command too short or empty, returning early');
      return;
    }
    
    console.log('🎯 STEP 2: Processing voice command immediately:', command);
    console.log('⏱️ STEP 2: Starting processing at:', new Date().toISOString());
    
    setIsProcessing(true);
    setResponse('Processing your voice command...');

    try {
      console.log('📡 STEP 3: Making API request to /api/chat');
      console.log('📡 STEP 3: Request payload:', { message: command });
      
      const startTime = Date.now();
      
      const response = await makeAuthenticatedRequest('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: command })
      });

      const requestTime = Date.now() - startTime;
      console.log('📡 STEP 4: API request completed in', requestTime, 'ms');
      console.log('📡 STEP 4: Response status:', response.status);
      console.log('📡 STEP 4: Response ok:', response.ok);

      const data = await response.json();
      console.log('🎙️ STEP 5: Voice command API response:', data);
      console.log('🎙️ STEP 5: Response parsing time:', Date.now() - startTime - requestTime, 'ms');
      
      if (response.ok) {
        const reply = data.reply || 'Command executed successfully';
        setResponse(reply);
        
        // Execute frontend actions immediately
        if (onVoiceCommand && data) {
          console.log('🎯 Executing voice command callback:', data);
          onVoiceCommand({
            ...data,
            transcript: command,
            source: 'voice_immediate'
          });
        }

        // Speak the response
        speakResponse(reply);
        
        // Clear transcript after processing
        setTimeout(() => {
          setTranscript('');
        }, 3000);
        
      } else {
        const errorMsg = data.error || 'Command not recognized. Try again.';
        setResponse(errorMsg);
        speakResponse(errorMsg);
      }
    } catch (error) {
      console.error('❌ Voice command processing error:', error);
      const errorMsg = 'Voice command failed. Please try again.';
      setResponse(errorMsg);
      speakResponse(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  // Text-to-speech response
  const speakResponse = (text) => {
    if (synthRef.current && text) {
      synthRef.current.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 0.7;
      synthRef.current.speak(utterance);
    }
  };

  // Manual listening toggle - SIMPLIFIED
  const toggleListening = async () => {
    console.log('🎛️ TOGGLE: toggleListening called, current isListening:', isListening);
    
    if (isListening) {
      console.log('🛑 TOGGLE: Stopping voice recognition');
      stopSpeechRecognition();
      setIsVADActive(false);
      if (vadRef.current) {
        cancelAnimationFrame(vadRef.current);
      }
    } else {
      console.log('🎤 TOGGLE: Starting voice recognition');
      
      // Request microphone permissions first
      try {
        console.log('🎤 TOGGLE: Requesting microphone permissions');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('✅ TOGGLE: Microphone permissions granted');
        
        // Stop the permission test stream
        stream.getTracks().forEach(track => track.stop());
        
        // Now start speech recognition
        startSpeechRecognition();
        
      } catch (error) {
        console.error('❌ TOGGLE: Microphone permission denied:', error);
        setResponse('Microphone access required. Please allow permissions and try again.');
        return;
      }
    }
  };

  // Manual text submission
  const handleManualSubmit = () => {
    console.log('📝 MANUAL: handleManualSubmit called with transcript:', `"${transcript}"`);
    if (transcript.trim() && !isProcessing) {
      console.log('📝 MANUAL: Processing manual transcript');
      processVoiceCommandImmediate(transcript.trim());
    } else {
      console.log('📝 MANUAL: Cannot process - transcript empty or already processing');
    }
  };

  // Handle text input change
  const handleTextChange = (e) => {
    setTranscript(e.target.value);
  };

  // Cleanup function - releases microphone and stops all processes
  const cleanup = () => {
    console.log('🧹 Cleaning up Enhanced Voice Assistant...');
    
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }
    if (vadRef.current) {
      cancelAnimationFrame(vadRef.current);
      vadRef.current = null;
    }
    if (vadTimeoutRef.current) {
      clearTimeout(vadTimeoutRef.current);
      vadTimeoutRef.current = null;
    }
    if (speechTimeoutRef.current) {
      clearTimeout(speechTimeoutRef.current);
      speechTimeoutRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    setIsListening(false);
    setVolume(0);
    setIsVADActive(false);
    console.log('🧹 Cleanup complete - microphone released');
  };

  // Toggle voice assistant panel
  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className={`voice-assistant ${isExpanded ? 'expanded' : ''}`}>
      {/* Voice Assistant Toggle Button */}
      <button 
        className={`voice-toggle ${isListening ? 'listening' : ''} ${isProcessing ? 'processing' : ''}`}
        onClick={toggleExpanded}
        title="Enhanced Voice Assistant"
      >
        <Mic size={20} />
        {isListening && (
          <div className="volume-indicator">
            <div 
              className="volume-bar" 
              style={{ 
                height: `${Math.max(10, (volume / 128) * 100)}%`,
                backgroundColor: isVADActive ? '#4CAF50' : '#2196F3'
              }}
            ></div>
          </div>
        )}
      </button>

      {/* Expanded Voice Assistant Panel */}
      {isExpanded && (
        <div className="voice-panel">
          <div className="voice-header">
            <h3>🎤 Voice Assistant</h3>
            <button className="close-btn" onClick={toggleExpanded} title="Close">
              <X size={16} />
            </button>
          </div>

          <div className="voice-content">
            {/* Status Display - Only show when there's content */}
            {(isListening || isProcessing) && (
              <div className="voice-status">
                {isListening && (
                  <div className="listening-indicator">
                    <div className="pulse"></div>
                    <span>Listening with VAD Active...</span>
                  </div>
                )}
                {isProcessing && (
                  <div className="processing-indicator">
                    <div className="spinner"></div>
                    <span>Processing Command...</span>
                  </div>
                )}
              </div>
            )}

            {/* Text Input Area */}
            <div className="voice-input">
              <textarea
                value={transcript}
                onChange={handleTextChange}
                placeholder="Voice commands appear here automatically, or type manually..."
                className="voice-textarea"
                rows="3"
                disabled={isProcessing}
              />
              
              <div className="voice-controls">
                <button
                  className={`mic-btn ${isListening ? 'listening' : ''}`}
                  onClick={toggleListening}
                  disabled={isProcessing || !speechSupported}
                  title={isListening ? 'Stop Listening' : 'Start Listening'}
                >
                  {isListening ? <MicOff size={20} /> : <Mic size={20} />}
                </button>
                
                <button
                  className="send-btn"
                  onClick={handleManualSubmit}
                  disabled={!transcript.trim() || isProcessing}
                  title="Execute Command"
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
              <p><strong>🎤 Enhanced Voice Commands with Real-time Detection:</strong></p>
              
              <div className="command-category">
                <p><strong>🏠 Navigation (Instant Action):</strong></p>
                <ul>
                  <li>"go to analytics" - Navigate immediately</li>
                  <li>"take me home" - Go to home page</li>
                  <li>"open habits" - View habits page</li>
                  <li>"go to settings" - Open settings</li>
                </ul>
              </div>

              <div className="command-category">
                <p><strong>🎯 Habit Management:</strong></p>
                <ul>
                  <li>"add habit to exercise daily"</li>
                  <li>"mark exercise as complete"</li>
                  <li>"show my habits"</li>
                  <li>"delete reading habit"</li>
                </ul>
              </div>

              <div className="vad-info">
                <p><strong>🔊 Voice Activity Detection (VAD):</strong></p>
                <ul>
                  <li>Automatically detects when you speak</li>
                  <li>Real-time voice level monitoring</li>
                  <li>Continuous listening with smart pause detection</li>
                  <li>Immediate command execution</li>
                </ul>
                <p><strong>💡 Just speak naturally - commands execute automatically!</strong></p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedVoiceAssistant;