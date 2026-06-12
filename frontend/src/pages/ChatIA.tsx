import React, { useState, useRef, useEffect } from 'react';
import {
  IonContent,
  IonPage,
  IonFooter,
  IonToolbar,
  IonIcon,
} from '@ionic/react';
import { micOutline, send } from 'ionicons/icons';
import './ChatIA.css';

interface Message {
  id: number;
  text: string;
  sender: 'bot' | 'user';
  time: string;
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
    text: `Bonjour ! Je suis votre assistant IA Anavid.

📊 Rapport du jour :
• Visiteurs : 1 247 (+12%)
• CA : 14 320 € (+8%)
• Alertes actives : 8

Comment puis-je vous aider ?`,
  },
];

const ChatIA: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputText, setInputText] = useState('');
  const contentRef = useRef<HTMLIonContentElement>(null);

  // Auto-scroll to bottom when new message arrives
  useEffect(() => {
    contentRef.current?.scrollToBottom(300);
  }, [messages]);

  const sendMessage = () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;

    const userMsg: Message = {
      id: Date.now(),
      text: trimmed,
      sender: 'user',
      time: getTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');

    // Simulate bot response
    setTimeout(() => {
      const botMsg: Message = {
        id: Date.now() + 1,
        text: "Je traite votre demande... 🤖",
        sender: 'bot',
        time: getTimeString(),
      };
      setMessages((prev) => [...prev, botMsg]);
    }, 1000);
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
            En ligne
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
              <div className={`bubble ${msg.sender}`}>
                <p className="bubble-text">{msg.text}</p>
                <span className="bubble-time">{msg.time}</span>
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
              className="chat-input"
              placeholder="Posez votre question..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button className="send-btn" onClick={sendMessage}>
              <IonIcon icon={send} />
            </button>
          </div>
        </IonToolbar>
      </IonFooter>
    </IonPage>
  );
};

export default ChatIA;
