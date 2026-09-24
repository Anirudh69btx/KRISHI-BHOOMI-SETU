/**
 * FLIP v3.0 — Updated KisanVoiceCopilot Component
 * Floating voice + text assistant with Whisper WASM STT, Piper TTS,
 * multilingual support, and NATS-backed RAG.
 */

import { useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useStore } from '../store';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export function KisanVoiceCopilot() {
  const { t } = useTranslation('common');
  const isOpen = useStore((s) => s.isOpen);
  const isListening = useStore((s) => s.isListening);
  const isSpeaking = useStore((s) => s.isSpeaking);
  const messages = useStore((s) => s.messages);
  const toggleOpen = useStore((s) => s.toggleOpen);
  const addMessage = useStore((s) => s.addMessage);
  const setListening = useStore((s) => s.setListening);
  const setSpeaking = useStore((s) => s.setSpeaking);
  const locale = useStore((s) => s.locale);
  const accessToken = useStore((s) => s.accessToken);
  const activeFarmId = useStore((s) => s.activeFarmId);

  const [textInput, setTextInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  /** Send text query to Rasa/RAG Copilot backend */
  const sendQuery = useCallback(async (text: string) => {
    if (!text.trim() || isProcessing) return;

    addMessage({ role: 'user', content: text, language: locale });
    setIsProcessing(true);
    setTextInput('');

    try {
      const res = await fetch(`${API_BASE}/api/v1/copilot/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({
          text,
          language: locale,
          farm_id: activeFarmId,
        }),
      });

      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json() as { text: string; language: string };

      addMessage({ role: 'assistant', content: data.text, language: data.language });

      // Speak response via browser TTS (fallback while Piper WASM loads)
      if ('speechSynthesis' in window && data.text) {
        const utterance = new SpeechSynthesisUtterance(data.text);
        utterance.lang = locale;
        utterance.rate = 0.9;
        setSpeaking(true);
        utterance.onend = () => setSpeaking(false);
        utterance.onerror = () => setSpeaking(false);
        window.speechSynthesis.speak(utterance);
      }
    } catch (err) {
      console.error('[Copilot] Query error:', err);
      addMessage({
        role: 'assistant',
        content: 'Sorry, I could not process your request. Please try again.',
        language: 'en',
      });
    } finally {
      setIsProcessing(false);
      scrollToBottom();
    }
  }, [isProcessing, locale, accessToken, activeFarmId, addMessage, setIsProcessing, setSpeaking, scrollToBottom]);

  /** Start voice recording via MediaRecorder */
  const startListening = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setListening(false);

        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (blob.size < 1000) return; // Too short, ignore

        // Send audio to Whisper transcription endpoint
        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        formData.append('language', locale);

        try {
          const res = await fetch(`${API_BASE}/api/v1/copilot/transcribe`, {
            method: 'POST',
            headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
            body: formData,
          });

          if (res.ok) {
            const data = await res.json() as { text: string };
            if (data.text.trim()) {
              await sendQuery(data.text);
            }
          }
        } catch (err) {
          console.error('[Copilot] Transcription error:', err);
        }
      };

      recorder.start(100); // 100ms chunks
      mediaRecorderRef.current = recorder;
      setListening(true);
    } catch (err) {
      console.error('[Copilot] Microphone error:', err);
      alert('Microphone access required for voice input. Please grant permission.');
    }
  }, [locale, accessToken, sendQuery, setListening]);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const handleMicClick = () => {
    if (isListening) {
      stopListening();
    } else {
      void startListening();
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <button
        id="copilot-fab"
        className={`copilot-fab ${isListening ? 'listening' : ''}`}
        onClick={toggleOpen}
        aria-label={t('nav.copilot')}
        title={t('nav.copilot')}
      >
        {isSpeaking ? '🔊' : isListening ? '🎙️' : '🌿'}
      </button>

      {/* Copilot Panel */}
      {isOpen && (
        <div className="copilot-panel" role="dialog" aria-label="Kisan Voice Copilot">
          {/* Header */}
          <div className="copilot-header">
            <span className="copilot-title">🌿 {t('nav.copilot')}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                {locale.toUpperCase()}
              </span>
              <button
                onClick={toggleOpen}
                className="banner-dismiss"
                aria-label="Close copilot"
              >
                ×
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="copilot-messages">
            {messages.length === 0 && (
              <div style={{
                textAlign: 'center',
                padding: '2rem 1rem',
                color: 'var(--color-text-muted)',
                fontSize: '0.875rem',
              }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🌾</div>
                <p>Namaste! I'm your Kisan Copilot.</p>
                <p style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                  Ask me about crop health, weather, or market prices — in your language.
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`copilot-message ${msg.role}`}>
                <div className="message-bubble">{msg.content}</div>
              </div>
            ))}

            {isProcessing && (
              <div className="copilot-message assistant">
                <div className="message-bubble" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                  <span style={{ animation: 'pulse 1s infinite 0s' }}>●</span>
                  <span style={{ animation: 'pulse 1s infinite 0.2s' }}>●</span>
                  <span style={{ animation: 'pulse 1s infinite 0.4s' }}>●</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Controls */}
          <div className="copilot-controls">
            {/* Mic button */}
            <button
              id="copilot-mic"
              className={`mic-btn ${isListening ? 'active' : ''}`}
              onClick={handleMicClick}
              aria-label={isListening ? 'Stop recording' : 'Start voice input'}
              title={isListening ? 'Stop' : 'Speak'}
            >
              {isListening ? '⏹️' : '🎤'}
            </button>

            {/* Text input */}
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void sendQuery(textInput);
                }
              }}
              placeholder="Type or speak your question..."
              disabled={isListening || isProcessing}
              style={{
                flex: 1,
                padding: '0.625rem 0.75rem',
                borderRadius: '0.5rem',
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg-elevated)',
                color: 'var(--color-text-primary)',
                fontSize: '0.875rem',
                outline: 'none',
              }}
            />

            {/* Send button */}
            <button
              onClick={() => void sendQuery(textInput)}
              disabled={!textInput.trim() || isProcessing}
              style={{
                padding: '0.625rem 1rem',
                borderRadius: '0.5rem',
                border: 'none',
                background: textInput.trim() ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                color: textInput.trim() ? 'white' : 'var(--color-text-muted)',
                cursor: textInput.trim() ? 'pointer' : 'not-allowed',
                fontSize: '1rem',
                transition: 'all 150ms ease',
              }}
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  );
}
