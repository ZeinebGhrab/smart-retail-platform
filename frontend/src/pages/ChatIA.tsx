import React, { useState, useRef, useEffect } from 'react';
import { IonContent, IonPage, IonFooter, IonToolbar, IonIcon } from '@ionic/react';
import { micOutline, send } from 'ionicons/icons';
import { API_BASE_URL } from '../services/api';
import { registerChatListener, unregisterChatListener } from '../services/chatBridge';
import './ChatIA.css';

interface Message {
  id: number; text: string; sender: 'bot' | 'user';
  time: string; loading?: boolean; model?: string;
}
interface RagResponse { answer: string; model?: string; error?: string; }
interface ChatHistoryItem { role: 'user' | 'assistant'; content: string; }

const now = () => {
  const d = new Date();
  return `${d.getHours()}h${String(d.getMinutes()).padStart(2, '0')}`;
};

const WELCOME: Message = {
  id: 0, sender: 'bot', time: '',
  text: "Bonjour ! Je suis votre assistant IA Anavid.\n\nJe réponds à vos questions sur les visiteurs grâce aux données réelles du magasin.\n\nExemples :\n• Nombre de visiteurs le 2026-05-30 ?\n• Flux horaire hier Porte_nord\n• Historique des 7 derniers jours\n• Prévision pour demain",
};

async function askRAG(question: string, history: ChatHistoryItem[]): Promise<RagResponse> {
  const res = await fetch(`${API_BASE_URL}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error((e as any).error || `Erreur ${res.status}`);
  }
  return res.json();
}

const ChatIA: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const contentRef = useRef<HTMLIonContentElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);
  const msgsRef    = useRef<Message[]>([WELCOME]);
  const sendRef    = useRef<(t: string) => void>(() => {});

  useEffect(() => { msgsRef.current = messages; }, [messages]);
  useEffect(() => { contentRef.current?.scrollToBottom(300); }, [messages]);

  useEffect(() => {
    registerChatListener((msg) => sendRef.current(msg));
    return () => unregisterChatListener();
  }, []);

  const triggerSend = async (text: string) => {
    const t = text.trim();
    if (!t || isLoading) return;
    const uid = Date.now();
    setMessages(p => [...p,
      { id: uid,     text: t,   sender: 'user', time: now() },
      { id: uid + 1, text: '…', sender: 'bot',  time: now(), loading: true },
    ]);
    setInputText('');
    setIsLoading(true);
    const history: ChatHistoryItem[] = msgsRef.current
      .filter(m => m.id !== 0 && !m.loading)
      .slice(-6)
      .map(m => ({ role: m.sender === 'user' ? 'user' : 'assistant', content: m.text }));
    try {
      const { answer, model, error } = await askRAG(t, history);
      setMessages(p => p.map(m =>
        m.loading ? { ...m, text: error ? `❌ ${error}` : answer, loading: false, time: now(), model } : m
      ));
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Erreur inconnue';
      setMessages(p => p.map(m =>
        m.loading ? { ...m, text: `❌ ${msg}`, loading: false } : m
      ));
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
      contentRef.current?.scrollToBottom(300);
    }
  };

  sendRef.current = triggerSend;

  return (
    <IonPage className="chat-page">
      <div className="chat-header">
        <button className="back-btn" aria-label="Retour">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M15 18l-6-6 6-6" stroke="#111827" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <div className="header-avatar">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="8" r="4" stroke="#2563eb" strokeWidth="2"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        <div className="header-info">
          <span className="header-title">Assistant IA — RAG</span>
          <span className="header-status">
            <span className="status-dot"/>
            {isLoading ? 'Llama 3.2 génère…' : 'Llama 3.2 · Ollama'}
          </span>
        </div>
      </div>

      <IonContent ref={contentRef} className="chat-content">
        <div className="messages-wrapper">
          {messages.map(msg => (
            <div key={msg.id} className={`msg-row ${msg.sender}`}>
              {msg.sender === 'bot' && (
                <div className="bot-avatar" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="8" r="4" stroke="#2563eb" strokeWidth="2"/>
                    <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
              )}
              <div className={`bubble ${msg.sender} ${msg.loading ? 'bubble-loading' : ''}`}>
                <p className="bubble-text">{msg.text}</p>
                {!msg.loading && msg.time && (
                  <div className="bubble-footer">
                    <span className="bubble-time">{msg.time}</span>
                    {msg.model && <span className="bubble-model">{msg.model.split(':')[0]}</span>}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </IonContent>

      <IonFooter className="chat-footer">
        <IonToolbar className="input-toolbar">
          <div className="input-row">
            <button className="mic-btn" aria-label="Microphone">
              <IonIcon icon={micOutline}/>
            </button>
            <input
              ref={inputRef}
              className="chat-input"
              placeholder="Posez votre question…"
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && triggerSend(inputText)}
              disabled={isLoading}
              aria-label="Question"
            />
            <button
              className={`send-btn ${isLoading ? 'send-btn-disabled' : ''}`}
              onClick={() => triggerSend(inputText)}
              disabled={isLoading}
              aria-label="Envoyer"
            >
              <IonIcon icon={send}/>
            </button>
          </div>
        </IonToolbar>
      </IonFooter>
    </IonPage>
  );
};

export default ChatIA;