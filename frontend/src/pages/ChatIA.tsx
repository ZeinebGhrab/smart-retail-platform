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

interface Message {
  id: number;
  text: string;
  sender: 'bot' | 'user';
  time: string;
  loading?: boolean;
}

const getTimeString = () => {
  const now = new Date();
  return `${now.getHours()}h${now.getMinutes().toString().padStart(2, '0')}`;
};

const initialMessages: Message[] = [
  {
    id: 1,
    sender: 'bot',
    time: getTimeString(),
    text: `Bonjour ! Je suis votre assistant IA Anavid.\n\nPosez-moi vos questions sur les visiteurs :\n• "Nombre de visiteurs le 2026-05-30 ?"\n• "Flux horaire hier Porte_nord"\n• "Historique des 7 derniers jours"\n• "Prévision pour demain"`,
  },
];

// ── Appel RAG backend ─────────────────────────────────────
async function askRAG(question: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`Erreur API (${res.status})`);
  const data = await res.json();
  return data.answer ?? 'Aucune réponse reçue.';
}

// ── Composant ─────────────────────────────────────────────
const ChatIA: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const contentRef = useRef<HTMLIonContentElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setInputText('');
    setIsLoading(true);

    try {
      const answer = await askRAG(trimmed);
      setMessages((prev) =>
        prev.map((m) =>
          m.loading ? { ...m, text: answer, loading: false, time: getTimeString() } : m
        )
      );
    } catch (err) {
      const errText = err instanceof Error ? err.message : 'Erreur inconnue';
      setMessages((prev) =>
        prev.map((m) =>
          m.loading
            ? { ...m, text: `❌ Impossible de contacter le serveur.\n${errText}`, loading: false }
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
        <button className="back-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M15 18l-6-6 6-6" stroke="white" strokeWidth="2"
              strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <div className="header-avatar">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="8" r="4" stroke="#60a5fa" strokeWidth="2"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="#60a5fa" strokeWidth="2"
              strokeLinecap="round"/>
          </svg>
        </div>
        <div className="header-info">
          <span className="header-title">Assistant IA</span>
          <span className="header-status">
            <span className="status-dot" />
            {isLoading ? 'En train de répondre…' : 'En ligne'}
          </span>
        </div>
      </div>

      {/* ── Messages ── */}
      <IonContent ref={contentRef} className="chat-content">
        <div className="messages-wrapper">
          {messages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.sender}`}>
              {msg.sender === 'bot' && (
                <div className="bot-avatar">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="8" r="4" stroke="#60a5fa" strokeWidth="2"/>
                    <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"
                      stroke="#60a5fa" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
              )}
              <div className={`bubble ${msg.sender} ${msg.loading ? 'bubble-loading' : ''}`}>
                <p className="bubble-text">{msg.text}</p>
                {!msg.loading && <span className="bubble-time">{msg.time}</span>}
              </div>
            </div>
          ))}
        </div>
      </IonContent>

      {/* ── Input Bar ── */}
      <IonFooter className="chat-footer">
        <IonToolbar className="input-toolbar">
          <div className="input-row">
            <button className="mic-btn">
              <IonIcon icon={micOutline} />
            </button>
            <input
              ref={inputRef}
              className="chat-input"
              placeholder="Posez votre question…"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button
              className={`send-btn ${isLoading ? 'send-btn-disabled' : ''}`}
              onClick={sendMessage}
              disabled={isLoading}
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