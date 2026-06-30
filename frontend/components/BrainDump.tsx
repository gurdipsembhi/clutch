"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

const PLACEHOLDER = `Dump everything on your mind, e.g.

CS assignment on graphs due tomorrow night, haven't started the report
PM interview at Acme on Thursday morning, need to prep STAR stories
pay electricity bill today before late fee
get mom a birthday gift this weekend
dentist Wednesday 3:30pm`;

export function BrainDump({ onAdded }: { onAdded: () => void }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (Ctor) setVoiceSupported(true);
    return () => recognitionRef.current?.abort();
  }, []);

  function toggleVoice() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      let finalChunk = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) finalChunk += result[0].transcript;
      }
      if (finalChunk) {
        setText((prev) => (prev ? `${prev.trim()} ${finalChunk.trim()}` : finalChunk.trim()));
      }
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
    setMsg("");
  }

  async function handleExtract() {
    if (!text.trim()) return;
    recognitionRef.current?.stop();
    setLoading(true);
    setMsg("");
    try {
      const res = await api.extract(text.trim());
      setText("");
      setMsg(`✓ Added ${res.count} task${res.count === 1 ? "" : "s"}`);
      onAdded();
      setTimeout(() => setMsg(""), 3500);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed to extract");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>🧠 Brain dump</h2>
        </div>
        <span className="sub">Gemini turns this into tasks</span>
      </div>
      <div className="card-body">
        <textarea
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={PLACEHOLDER}
          disabled={loading}
        />
        <div className="row between mt12">
          <div className="row" style={{ gap: 10 }}>
            {voiceSupported && (
              <button
                className={`mic-btn ${listening ? "recording" : ""}`}
                onClick={toggleVoice}
                disabled={loading}
                title={listening ? "Stop dictation" : "Dictate your brain-dump"}
              >
                {listening ? "● Listening…" : "🎤 Speak"}
              </button>
            )}
            <span className="sub" style={{ color: msg.startsWith("✓") ? "var(--success)" : "var(--muted)" }}>
              {msg}
            </span>
          </div>
          <button className="primary-btn" onClick={handleExtract} disabled={loading || !text.trim()}>
            {loading ? <span className="spinner" /> : "Extract tasks →"}
          </button>
        </div>
      </div>
    </div>
  );
}
