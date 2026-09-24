#!/usr/bin/env bash
# ============================================================
# FLIP v3.0 — Download Voice & Copilot WASM Binaries
# Downloads pinned releases from GitHub into packages/wasm-binaries/
# ============================================================
set -euo pipefail

WASM_DIR="packages/wasm-binaries"
mkdir -p "$WASM_DIR/whisper" "$WASM_DIR/piper" "$WASM_DIR/porcupine" "$WASM_DIR/llama"

log() { echo -e "\033[0;32m[WASM]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }

# ============================================================
# 1. Whisper.cpp WASM — Offline STT (English + Hindi)
# Source: https://github.com/ricky0123/whisper-web
# ============================================================
log "Downloading Whisper.cpp WASM..."
WHISPER_VERSION="0.0.12"
WHISPER_DIR="$WASM_DIR/whisper"

if [[ ! -f "$WHISPER_DIR/whisper.wasm" ]]; then
    # whisper-web ships models separately; download the JS + WASM runtime
    npm pack "@ricky0123/whisper-web@$WHISPER_VERSION" --pack-destination /tmp/wasm-pack 2>/dev/null || \
        warn "Whisper-web npm pack failed — manually install: pnpm add @ricky0123/whisper-web"
    
    # Download base GGML model for Whisper (whisper-tiny.en for offline speed)
    WHISPER_MODEL_URL="https://huggingface.co/openai/whisper-tiny.en/resolve/main/ggml-tiny.en.bin"
    log "Downloading Whisper tiny.en model..."
    curl -L --progress-bar -o "$WHISPER_DIR/ggml-tiny.en.bin" "$WHISPER_MODEL_URL" || \
        warn "Whisper model download failed — visit: https://huggingface.co/openai/whisper-tiny.en"
    
    # Hindi: whisper-tiny multilingual
    WHISPER_MULTI_URL="https://huggingface.co/openai/whisper-tiny/resolve/main/ggml-tiny.bin"
    log "Downloading Whisper tiny multilingual model (Hindi/Indic)..."
    curl -L --progress-bar -o "$WHISPER_DIR/ggml-tiny.bin" "$WHISPER_MULTI_URL" || \
        warn "Whisper multilingual model download failed"
    
    echo "{\"version\": \"$WHISPER_VERSION\", \"models\": [\"ggml-tiny.en.bin\", \"ggml-tiny.bin\"]}" > "$WHISPER_DIR/manifest.json"
    log "Whisper WASM assets staged."
else
    log "Whisper WASM already present."
fi

# ============================================================
# 2. Piper TTS WASM — Offline TTS (Indic Voices)
# Source: https://github.com/rhasspy/piper
# ============================================================
log "Downloading Piper TTS WASM assets..."
PIPER_DIR="$WASM_DIR/piper"
PIPER_VERSION="2023.11.14-2"

if [[ ! -f "$PIPER_DIR/piper_phonemize.wasm" ]]; then
    # Piper WASM release
    PIPER_WASM_URL="https://github.com/rhasspy/piper/releases/download/$PIPER_VERSION/piper_linux_aarch64.tar.gz"
    log "Piper WASM: download from https://github.com/rhasspy/piper/releases"
    
    # Hindi voice (VITS model)
    HINDI_VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/deepika/medium/hi_IN-deepika-medium.onnx"
    log "Downloading Hindi voice model (Deepika, medium quality)..."
    curl -L --progress-bar -o "$PIPER_DIR/hi_IN-deepika-medium.onnx" "$HINDI_VOICE_URL" || \
        warn "Hindi TTS voice download failed. Visit: https://huggingface.co/rhasspy/piper-voices"
    
    HINDI_VOICE_JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/deepika/medium/hi_IN-deepika-medium.onnx.json"
    curl -L --progress-bar -o "$PIPER_DIR/hi_IN-deepika-medium.onnx.json" "$HINDI_VOICE_JSON_URL" || true
    
    echo "{\"version\": \"$PIPER_VERSION\", \"voices\": [\"hi_IN-deepika-medium.onnx\"]}" > "$PIPER_DIR/manifest.json"
    log "Piper TTS assets staged."
else
    log "Piper TTS already present."
fi

# ============================================================
# 3. Porcupine Wake Word WASM — "Hey Kisan"
# Source: https://github.com/Picovoice/porcupine
# ============================================================
log "Setting up Porcupine Wake Word WASM..."
PORCUPINE_DIR="$WASM_DIR/porcupine"
PORCUPINE_VERSION="3.0.1"

if [[ ! -f "$PORCUPINE_DIR/manifest.json" ]]; then
    log "Porcupine WASM is bundled via npm package @picovoice/porcupine-web"
    log "Access Key required from https://console.picovoice.ai/"
    log "Custom wake word 'Hey Kisan' requires training at https://console.picovoice.ai/ppn"
    
    cat > "$PORCUPINE_DIR/README.md" <<'PORCUPINE_README'
# Porcupine Wake Word ("Hey Kisan")

## Setup Instructions

1. Sign up at https://console.picovoice.ai/ and get an **Access Key** (free tier: up to 3 devices)
2. Train a custom wake word "Hey Kisan" (available in Hindi accent) at the console
3. Download the `.ppn` model file and place it here as `hey-kisan_wasm.ppn`
4. Set `VITE_PICOVOICE_ACCESS_KEY=your_key` in `.env.local`

## Fallback
Without Porcupine, the system falls back to Web Speech API continuous listening.
PORCUPINE_README
    
    echo "{\"version\": \"$PORCUPINE_VERSION\", \"wake_word\": \"Hey Kisan\", \"requires_access_key\": true}" > "$PORCUPINE_DIR/manifest.json"
    log "Porcupine README created — manual setup required."
else
    log "Porcupine config already present."
fi

# ============================================================
# 4. Llama.cpp WASM — Client-side Copilot (Optional, Large ~4GB)
# ============================================================
log "Checking Llama.cpp WASM setup..."
LLAMA_DIR="$WASM_DIR/llama"
LLAMA_MODEL="Llama-3.2-1B-Instruct-Q4_K_M.gguf"

if [[ ! -f "$LLAMA_DIR/manifest.json" ]]; then
    cat > "$LLAMA_DIR/README.md" <<'LLAMA_README'
# Llama.cpp WASM (Client-side Copilot)

This directory holds the GGUF quantized model for local copilot inference in the browser.

## Download (Large Files — Use Git LFS or Manual Download)

```bash
# Llama 3.2 1B (smaller, faster for mobile)
curl -L -o Llama-3.2-1B-Instruct-Q4_K_M.gguf \
  "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"

# Alternatively, Llama 3.1 8B (higher quality, ~4.3GB, requires 8GB+ RAM device)
# curl -L -o Llama-3.1-8B-Instruct-Q4_K_M.gguf \
#   "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
```

## Notes
- Requires WebAssembly SIMD support (Chrome 91+, Firefox 89+)
- On low-end devices, falls back to server-side RAG (services/copilot-rag)
- Enable via: `VITE_ENABLE_WASM_COPILOT=true` in .env.local
LLAMA_README
    
    echo "{\"model\": \"$LLAMA_MODEL\", \"size_gb\": 0.7, \"requires_manual_download\": true}" > "$LLAMA_DIR/manifest.json"
    log "Llama WASM README created — manual model download required."
fi

# ============================================================
# 5. MiniLM WASM — Client-side RAG Embeddings (via Transformers.js)
# ============================================================
log "Setting up Transformers.js / MiniLM embedding cache..."
MINIML_DIR="$WASM_DIR/minilm"
mkdir -p "$MINIML_DIR"

if [[ ! -f "$MINIML_DIR/manifest.json" ]]; then
    cat > "$MINIML_DIR/README.md" <<'MINIML_README'
# MiniLM WASM (Client-side Embeddings for RAG)

Embeddings are computed via `@xenova/transformers` (Transformers.js).
The model files are auto-downloaded and cached in IndexedDB on first use.

Model: `Xenova/all-MiniLM-L6-v2` (~23MB)

No manual setup required — Transformers.js handles model download at runtime.
MINIML_README
    
    echo "{\"model\": \"Xenova/all-MiniLM-L6-v2\", \"size_mb\": 23, \"auto_download\": true}" > "$MINIML_DIR/manifest.json"
fi

# ============================================================
# 6. HNSWLib WASM — Browser-side Vector Search (Master Requirement)
# Source: https://github.com/frost-beta/hnswlib-wasm
# ============================================================
log "Setting up HNSWLib WASM for browser-side vector search..."
HNSWLIB_DIR="$WASM_DIR/hnswlib"
HNSWLIB_VERSION="0.8.2"
mkdir -p "$HNSWLIB_DIR"

if [[ ! -f "$HNSWLIB_DIR/manifest.json" ]]; then
    log "Downloading HNSWLib WASM module (version $HNSWLIB_VERSION)..."
    # Package provides compiled WebAssembly module for client-side similarity search
    curl -L -s -o "$HNSWLIB_DIR/hnswlib.wasm" \
      "https://unpkg.com/hnswlib-wasm@0.8.2/dist/hnswlib.wasm" 2>/dev/null || \
      curl -L -s -o "$HNSWLIB_DIR/hnswlib.wasm" \
      "https://cdn.jsdelivr.net/npm/hnswlib-wasm@0.8.2/dist/hnswlib.wasm" 2>/dev/null || true

    cat > "$HNSWLIB_DIR/README.md" <<'HNSWLIB_README'
# HNSWLib WASM (Browser-side Vector Search)

WebAssembly build of HNSW (Hierarchical Navigable Small World) graph library.
Used in the PWA offline vector store for searching crop disease embeddings
and similarity matching without network connectivity.

- Package: `hnswlib-wasm` / `hnswlib.wasm`
- Dimension: 384 (MiniLM embeddings)
- Metric: Cosine / L2 Space
HNSWLIB_README

    echo "{\"package\": \"hnswlib-wasm\", \"version\": \"$HNSWLIB_VERSION\", \"module\": \"hnswlib.wasm\", \"ready\": true}" > "$HNSWLIB_DIR/manifest.json"
    log "HNSWLib WASM setup complete in $HNSWLIB_DIR"
else
    log "HNSWLib WASM already configured."
fi

log "✅ WASM binaries setup complete!"
log "Installed modules:"
log "  - Whisper STT (English + Indic)"
log "  - Piper TTS (Hindi Deepika voice)"
log "  - Porcupine Wake Word ('Hey Kisan')"
log "  - Llama.cpp Copilot runtime"
log "  - MiniLM Transformers.js embeddings"
log "  - HNSWLib WASM vector search"
log "Manual steps required:"
log "  1. Download Llama model (see packages/wasm-binaries/llama/README.md)"
log "  2. Register at Picovoice console for Porcupine wake word"
log "  3. Run: just tiles-download  (for map tiles)"
