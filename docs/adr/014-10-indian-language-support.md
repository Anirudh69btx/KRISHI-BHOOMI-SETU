# ADR-014: 10 Indian Language Support + Voice Interface

- **Status**: Accepted
- **Date**: 2025-02-15
- **Deciders**: Product + Platform Team

## Context

FLIP targets smallholder farmers across India where smartphone literacy varies significantly. Many farmers are more comfortable speaking in their native language than reading. The platform must:
1. Support text display in 10 major Indian languages
2. Enable voice input (speech-to-text) entirely on-device for privacy + offline use
3. Enable voice output (text-to-speech) for low-literacy users
4. Not require cloud API calls for voice (ADR-004 offline-first)

## Decision

### Languages
Support English + 10 Indian languages:
`hi, te, ta, kn, ml, pa, gu, mr, or` using **i18next** with:
- Lazy-loaded JSON namespace files per language
- Browser language detection with localStorage persistence
- RTL support hooks (none of the 10 are RTL, but infrastructure ready)

### Voice Input (STT)
**Whisper WASM** (whisper.cpp compiled to WebAssembly):
- Model: `whisper-small` for `hi, en` (multilingual)
- Runs entirely in browser — no audio leaves device
- Supports Web Audio API microphone capture
- Language auto-detect or forced locale from user settings

### Voice Output (TTS)
**Piper TTS** compiled to WASM:
- Supports `hi, en` initially (expand to other languages as ONNX models become available)
- Sub-200ms latency for short advisory messages
- Falls back to browser SpeechSynthesis API for unsupported languages

### Copilot (RAG)
- `distiluse-base-multilingual-cased-v2` for multilingual embeddings
- Stored as `vector(768)` in pgvector
- Rasa NLU handles intent classification in Hindi/English

## Consequences

**Positive:**
- Privacy-preserving (no audio to cloud)
- Fully offline voice operation
- 10 language support covers 95%+ of Indian farmers

**Negative:**
- WASM bundle adds ~50MB (mitigated by cache-first SW strategy)
- Piper TTS models are 30-60MB each (downloaded on demand)
- Whisper accuracy drops for code-switched speech (Hinglish)

## Alternatives Considered

- Google Cloud Speech API (rejected: privacy, cost, offline requirement)
- Azure Cognitive Services (rejected: same reasons)
- Bhashini (ULCA) API (considered for future: promising but requires connectivity)
