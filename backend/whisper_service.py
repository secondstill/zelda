"""
Whisper-large Audio Processing Service for Zelda AI Assistant

This module handles audio transcription using Whisper-large model and integrates
with the chat pipeline for seamless voice-to-text conversion.
"""

import os
import tempfile
import torch
import whisper
import numpy as np
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperService:
    """Service class for handling Whisper audio transcription (large-v3 only, lazy loaded).

    Simplified per requirements:
    - Always load 'large-v3' model (no environment overrides, no fallbacks)
    - Lazy load on first use; cache instance globally
    - Status reporting for readiness endpoint
    """

    def __init__(self):
        self.model = None
        self.device = self._detect_device()
        self.model_name = None
        self.load_attempted = False
        self.last_error: Optional[str] = None

    def _detect_device(self) -> str:
        # Always start with CPU, never use MPS
        logger.info("Using CPU for Whisper processing (MPS disabled)")
        return "cpu"

    def ensure_model_loaded(self):
        """Load the model on CPU first, fallback to CUDA if CPU fails."""
        if self.model is not None:
            logger.info(f"✅ Whisper model '{self.model_name}' already loaded on {self.device}")
            return
        if self.load_attempted:
            raise RuntimeError(self.last_error or "Previous model load attempt failed")
        self.load_attempted = True
        target = "large-v3"
        # Try CPU first
        logger.info(f"🔄 Loading Whisper model '{target}' on CPU from cache...")
        try:
            self.model = whisper.load_model(target, device="cpu")
            self.model_name = target
            self.device = "cpu"
            self.last_error = None
            logger.info(f"✅ Whisper model '{target}' loaded successfully on CPU (cached)")
            return
        except Exception as cpu_e:
            logger.error(f"Failed to load Whisper model '{target}' on CPU: {cpu_e}")
            self.last_error = str(cpu_e)
            # Try CUDA if available
            if torch.cuda.is_available():
                try:
                    logger.info(f"🔄 Loading Whisper model '{target}' on CUDA...")
                    self.model = whisper.load_model(target, device="cuda")
                    self.model_name = target
                    self.device = "cuda"
                    self.last_error = None
                    logger.info(f"✅ Whisper model '{target}' loaded successfully on CUDA")
                    return
                except Exception as cuda_e:
                    self.last_error = str(cuda_e)
                    logger.error(f"Failed to load Whisper model '{target}' on CUDA: {cuda_e}")
            raise RuntimeError(self.last_error)

    def get_status(self) -> Dict[str, Any]:
        """Return readiness & configuration info for health endpoint."""
        return {
            "ready": self.model is not None,
            "model": self.model_name,
            "device": self.device,
            "attempted": self.load_attempted,
            "error": self.last_error,
        }
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper-large-v3, always in English.
        Tries CPU first, then CUDA if CPU fails.
        """
        if self.model is None:
            self.ensure_model_loaded()

        # Always use English language
        language = "en"

        try:
            logger.info(f"Starting transcription of {audio_file_path} (lang=en)")
            # Enhanced transcription with optimized parameters for all app commands
            result = self.model.transcribe(
                audio_file_path,
                language=language,
                task="transcribe",
                temperature=0.0,  # Deterministic output
                best_of=3,  # Reduced for speed
                beam_size=3,  # Reduced for speed  
                patience=1.0,  # Reduced patience
                suppress_tokens=[-1],
                initial_prompt="Go to analytics. Add a habit to exercise. Open settings. Show habits. Mark complete. Navigate home. Log out. Refresh page.",  # Comprehensive app commands context
                word_timestamps=True,
                prepend_punctuations="\"'([{-",
                append_punctuations="\"'.,:)]!?",
                fp16=False,  # Use FP32 for better accuracy on CPU
                no_speech_threshold=0.2,  # Even lower threshold
                logprob_threshold=-1.0,  # More sensitive
                condition_on_previous_text=False,  # Don't use previous context that might confuse
                compression_ratio_threshold=2.4,  # Default compression threshold
                length_penalty=1.0  # No length penalty
            )
            text = result.get("text", "").strip()
            language_detected = result.get("language", "unknown")
            segments = result.get("segments", [])
            confidence = self._calculate_confidence(segments)
            logger.info(f"Transcription complete: '{text[:50]}...' (confidence: {confidence:.2f})")
            return {
                "success": True,
                "text": text,
                "language": language_detected,
                "confidence": confidence,
                "duration": segments[-1]["end"] if segments else 0,
                "word_count": len(text.split()) if text else 0,
                "segments": segments
            }
        except Exception as e:
            import traceback
            tb = traceback.format_exc(limit=6)
            error_msg = str(e)
            self.last_error = error_msg
            last_error_class = e.__class__.__name__
            logger.error(f"Transcription failed on device {self.device}: {error_msg}")
            retry_hint = None

            # If CPU fails, try CUDA
            if self.device == "cpu" and torch.cuda.is_available():
                try:
                    logger.info("Attempting CUDA fallback after CPU failure...")
                    cuda_model = whisper.load_model("large-v3", device="cuda")
                    cuda_result = cuda_model.transcribe(
                        audio_file_path,
                        language="en",
                        task="transcribe",
                        temperature=0.0,
                        best_of=3,
                        beam_size=3,
                        word_timestamps=True
                    )
                    text = cuda_result.get("text", "").strip()
                    segments = cuda_result.get("segments", [])
                    confidence = self._calculate_confidence(segments)
                    logger.info("CUDA retry succeeded after CPU failure")
                    retry_hint = "cuda_retry_success"
                    return {
                        "success": True,
                        "text": text,
                        "language": cuda_result.get("language", "unknown"),
                        "confidence": confidence,
                        "duration": segments[-1]["end"] if segments else 0,
                        "word_count": len(text.split()) if text else 0,
                        "segments": segments,
                        "note": "Processed via CUDA fallback after initial CPU error"
                    }
                except Exception as cuda_e:
                    cuda_tb = traceback.format_exc(limit=4)
                    logger.error(f"CUDA retry failed: {cuda_e}")
                    error_msg += f" | CUDA retry failed: {cuda_e}"
                    tb += "\nCUDA RETRY TRACE:\n" + cuda_tb
                    retry_hint = "cuda_retry_failed"

            return {
                "success": False,
                "error": error_msg,
                "error_class": last_error_class,
                "trace": tb[-2000:],
                "retry_hint": retry_hint,
                "text": "",
                "confidence": 0.0
            }
    
    def _calculate_confidence(self, segments) -> float:
        """Calculate average confidence score from segments"""
        if not segments:
            return 0.0
        
        # Whisper doesn't provide direct confidence, so we estimate based on
        # segment probability and other factors
        total_prob = 0.0
        total_duration = 0.0
        
        for segment in segments:
            # Use segment-level probability if available
            prob = segment.get("avg_logprob", -1.0)
            duration = segment.get("end", 0) - segment.get("start", 0)
            
            # Convert log probability to confidence score
            confidence = min(1.0, max(0.0, np.exp(prob)))
            
            total_prob += confidence * duration
            total_duration += duration
        
        return total_prob / total_duration if total_duration > 0 else 0.0
    
    def process_audio_bytes(self, audio_bytes: bytes, filename_hint: str = "audio.webm") -> Dict[str, Any]:
        """
        Process audio from bytes (from frontend upload)
        
        Args:
            audio_bytes: Raw audio data
            filename_hint: Hint for file extension/format
            
        Returns:
            Transcription results
        """
        try:
            # Create temporary file
            suffix = self._get_file_suffix(filename_hint)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Transcribe the temporary file
                result = self.transcribe_audio(temp_file_path)
                return result
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass  # Ignore cleanup errors
                    
        except Exception as e:
            logger.error(f"Failed to process audio bytes: {str(e)}")
            return {
                "success": False,
                "error": f"Audio processing failed: {str(e)}",
                "text": "",
                "confidence": 0.0
            }
    
    def _get_file_suffix(self, filename: str) -> str:
        """Extract file suffix from filename"""
        if '.' in filename:
            return '.' + filename.split('.')[-1]
        return '.webm'  # Default
    
    def is_ready(self) -> bool:
        """Check if the Whisper service is ready to process audio"""
        return self.model is not None

# Global service instance
_whisper_service = None

def get_whisper_service() -> WhisperService:
    """Get the global Whisper service instance"""
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService()
    return _whisper_service

def transcribe_audio_file(audio_file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for audio file transcription"""
    service = get_whisper_service()
    return service.transcribe_audio(audio_file_path, language)

def transcribe_audio_bytes(audio_bytes: bytes, filename_hint: str = "audio.webm") -> Dict[str, Any]:
    """Convenience function for audio bytes transcription"""
    service = get_whisper_service()
    return service.process_audio_bytes(audio_bytes, filename_hint)