# Voice / Whisper Service Status

This service now uses a single fixed model: `large-v3` (OpenAI Whisper). The model is downloaded and initialized lazily on first transcription to avoid slowing initial server startup.

## Key Points
* Model: `large-v3` only (no environment overrides, no fallbacks)
* Load Strategy: Lazy (first `/api/voice/audio` call triggers download + init)
* Status Endpoint: `GET /api/voice/status` (unauthenticated)

## Status Endpoint
Example response before first use:
```
{
  "success": true,
  "status": {
    "whisper_enabled": true,
    "ready": false,
    "model": null,
    "device": "mps|cuda|cpu",
    "attempted": false,
    "error": null
  }
}
```
After successful load:
```
{
  "success": true,
  "status": {
    "whisper_enabled": true,
    "ready": true,
    "model": "large-v3",
    "device": "mps|cuda|cpu",
    "attempted": true,
    "error": null
  }
}
```

## Audio Transcription Endpoint
`POST /api/voice/audio` (auth required)

Multipart form-data field: `audio` (binary). Returns transcript + processed reply.

Error codes:
* `WHISPER_DISABLED` – Dependencies not installed.
* `MODEL_LOAD_FAILED` – The `large-v3` model failed to download or initialize.
* `TRANSCRIPTION_ERROR` – Exception during transcription pipeline.
* `TRANSCRIBE_FAIL` – Model returned failure object.
* `VOICE_AUDIO_ERROR` – Generic top-level exception.

## Frontend Integration Hints
1. Poll `/api/voice/status` on load; hide microphone until `whisper_enabled`.
2. If `attempted=false` and user clicks record: show “Downloading speech model (first use)...”.
3. If `error` present while `ready=false`: suggest server restart or checking disk/RAM.

## Troubleshooting
| Symptom | Possible Cause | Action |
|--------|----------------|-------|
| `MODEL_LOAD_FAILED` | Insufficient RAM / GPU VRAM | Restart after freeing memory; if persistent, consider swapping to a lighter model in future updates. |
| Very slow first request | Large model download (~3GB) | Be patient; subsequent requests are fast. |
| MPS backend errors | Torch build mismatch | Reinstall PyTorch with MPS support or fallback to CPU (Apple Silicon). |
| `TRANSCRIPTION_ERROR` | Corrupt or unsupported audio | Ensure webm/opus from browser; try wav conversion. |
| `TRANSCRIBE_FAIL` + `PythonFallbackKernel` | Torch kernel dispatch issue | Reinstall torch/torchaudio; ensure versions match and upgrade to latest stable. |
| `retry_hint=cpu_retry_success` | GPU/MPS failed first | Performance reduced; investigate driver / MPS issues if frequent. |
| `retry_hint=cpu_retry_failed` | Both device & CPU attempts failed | Check system memory pressure, reinstall dependencies. |

### Advanced Debug Fields
`/api/voice/audio` error responses now include:
* `error_class` – Python exception type.
* `retry_hint` – `cpu_retry_success` or `cpu_retry_failed` where applicable.
* `hint` – User-friendly remediation guidance.

If you see low-level ATen / kernel errors:
1. Verify Python version matches torch build.
2. Reinstall dependencies:
  ```bash
  pip install --upgrade --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```
3. Test minimal transcription using a short wav to isolate frontend encoding issues.

## Notes
* Loading is attempted only once per process; after a failure you must restart the backend to retry.
* Ensure `ffmpeg` is installed for optimal codec handling.
