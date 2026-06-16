import React, { useState, useRef, useEffect } from 'react';
import {
  IonContent,
  IonPage,
  IonFooter,
  IonToolbar,
  IonIcon,
} from '@ionic/react';
import { micOutline, send } from 'ionicons/icons';
import { API_BASE_URL } from '../services/api';
import './ChatIA.css';

// ── Types ─────────────────────────────────────────────────
interface Message {
  id: number;
  text: string;
  sender: 'bot' | 'user';
  time: string;
  loading?: boolean;
  model?: string;         // modèle Ollama utilisé (affiché sous la bulle)
}

interface RagResponse {
  answer: string;
  model?: string;
  sources?: { csv: string; vector_db: string };
  error?: string;
}

interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

// ── Helpers ───────────────────────────────────────────────
const getTimeString = () => {
  const now = new Date();
  return `${now.getHours()}h${now.getMinutes().toString().padStart(2, '0')}`;
};

const initialMessages: Message[] = [
  {
    id: 1,
    sender: 'bot',
    time: getTimeString(),
    text: `Bonjour ! Je suis votre assistant IA Anavid.\n\nJe réponds à vos questions sur les visiteurs grâce aux données réelles du magasin.\n\nExemples :\n• Nombre de visiteurs le 2026-05-30 ?\n• Flux horaire hier Porte_nord\n• Historique des 7 derniers jours\n• Prévision pour demain`,
  },
];

// ── Appel RAG — POST /api/chat/ ───────────────────────────
async function askRAG(question: string, history: ChatHistoryItem[] = []): Promise<RagResponse> {
  const res = await fetch(`${API_BASE_URL}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Erreur API (${res.status})`);
  }
  return res.json();
}

// ── Composant ─────────────────────────────────────────────
const ChatIA: React.FC = () => {
  const [messages, setMessages]   = useState<Message[]>(initialMessages);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const contentRef = useRef<HTMLIonContentElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);

  useEffect(() => {
    contentRef.current?.scrollToBottom(300);
  }, [messages]);

  const sendMessage = async () => {
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;

    const userMsg: Message = {
      id: Date.now(),
      text: trimmed,
      sender: 'user',
      time: getTimeString(),
    };
    const loadingMsg: Message = {
      id: Date.now() + 1,
      text: '...',
      sender: 'bot',
      time: getTimeString(),
      loading: true,
    };

    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setInputText('');
    setIsLoading(true);

    // Historique = messages précédents (hors message d'accueil initial
    // et hors bulle de chargement courante), limité aux 6 derniers.
    const history: ChatHistoryItem[] = messages
      .filter(m => m.id !== initialMessages[0].id && !m.loading)
      .slice(-6)
      .map(m => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text,
      }));

    try {
      const { answer, model, error } = await askRAG(trimmed, history);
      const text = error ? `❌ ${error}` : answer;
      setMessages(prev =>
        prev.map(m =>
          m.loading
            ? { ...m, text, loading: false, time: getTimeString(), model }
            : m
        )
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erreur inconnue';
      setMessages(prev =>
        prev.map(m =>
          m.loading
            ? { ...m, text: `❌ Impossible de contacter le serveur.\n${msg}`, loading: false }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') sendMessage();
  };

  return (
    <IonPage className="chat-page">

      {/* ── Header ── */}
      <div className="chat-header">
        <button className="back-btn" aria-label="Retour">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M15 18l-6-6 6-6" stroke="#111827" strokeWidth="2"
              strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <div className="header-avatar">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="8" r="4" stroke="#2563eb" strokeWidth="2"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="#2563eb" strokeWidth="2"
              strokeLinecap="round"/>
          </svg>
        </div>
        <div className="header-info">
          <span className="header-title">Assistant IA — RAG</span>
          <span className="header-status">
            <span className="status-dot" />
            {isLoading ? 'Llama 3.2 génère…' : 'Llama 3.2 · Ollama'}
          </span>
        </div>
      </div>

      {/* ── Messages ── */}
      <IonContent ref={contentRef} className="chat-content">
        <div className="messages-wrapper">
          {messages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.sender}`}>
              {msg.sender === 'bot' && (
                <div className="bot-avatar" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="8" r="4" stroke="#2563eb" strokeWidth="2"/>
                    <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"
                      stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
              )}
              <div className={`bubble ${msg.sender} ${msg.loading ? 'bubble-loading' : ''}`}>
                <p className="bubble-text">{msg.text}</p>
                {!msg.loading && (
                  <div className="bubble-footer">
                    <span className="bubble-time">{msg.time}</span>
                    {msg.model && (
                      <span className="bubble-model" title="Modèle utilisé">
                        {msg.model.split(':')[0]}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </IonContent>

      {/* ── Input ── */}
      <IonFooter className="chat-footer">
        <IonToolbar className="input-toolbar">
          <div className="input-row">
            <button className="mic-btn" aria-label="Microphone">
              <IonIcon icon={micOutline} />
            </button>
            <input
              ref={inputRef}
              className="chat-input"
              placeholder="Posez votre question…"
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              aria-label="Question"
            />
            <button
              className={`send-btn ${isLoading ? 'send-btn-disabled' : ''}`}
              onClick={sendMessage}
              disabled={isLoading}
              aria-label="Envoyer"
            >
              <IonIcon icon={send} />
            </button>
          </div>
        </IonToolbar>
      </IonFooter>
    </IonPage>
  );
};

export default ChatIA;