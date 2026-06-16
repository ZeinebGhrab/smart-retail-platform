import { useState, useEffect, useRef, useCallback } from 'react';
import { PredictionData } from '../types/dashboard.types';
import { API_BASE_URL } from '../services/api';

interface UseSSEPredictionReturn {
  prediction: PredictionData | null;
  isConnected: boolean;
  lastReceivedAt: Date | null;
  error: string | null;
}

/**
 * useSSEPrediction
 * Connects to Django SSE endpoint: GET /api/prediction/stream/
 * Receives push payloads from n8n "Push Notification (SSE)" node.
 *
 * Django endpoint example:
 *   GET /api/prediction/stream/  →  text/event-stream
 *   Each event: event: llm_report\ndata: { ...PredictionData }
 *
 * n8n node "Push SSE → Django" should POST to:
 *   POST /api/daily-report/
 *   body: JSON PredictionData
 * Django then buffers it and pushes via SSE to all connected clients.
 */
export function useSSEPrediction(): UseSSEPredictionReturn {
  const [prediction, setPrediction]       = useState<PredictionData | null>(null);
  const [isConnected, setIsConnected]     = useState(false);
  const [lastReceivedAt, setLastReceivedAt] = useState<Date | null>(null);
  const [error, setError]                 = useState<string | null>(null);
  const esRef    = useRef<EventSource | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
    }

    const url = `${API_BASE_URL}/prediction/stream/`;
    const es  = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    // Événements génériques (sans nom) — keepalive ou fallback
    es.onmessage = (event: MessageEvent) => {
      try {
        const data: PredictionData = JSON.parse(event.data);
        setPrediction(data);
        setLastReceivedAt(new Date());
      } catch (e) {
        console.error('[SSE] Parse error (onmessage):', e);
      }
    };

    // FIX #3 : écouter "llm_report" — nom exact émis par Django views.py
    // yield f"event: llm_report\ndata: {json.dumps(payload)}\n\n"
    es.addEventListener('llm_report', (event: MessageEvent) => {
      try {
        const data: PredictionData = JSON.parse(event.data);
        setPrediction(data);
        setLastReceivedAt(new Date());
      } catch (e) {
        console.error('[SSE] llm_report event parse error:', e);
      }
    });

    // Garde l'écouteur "prediction" au cas où le nom changerait à nouveau
    es.addEventListener('prediction', (event: MessageEvent) => {
      try {
        const data: PredictionData = JSON.parse(event.data);
        setPrediction(data);
        setLastReceivedAt(new Date());
      } catch (e) {
        console.error('[SSE] prediction event parse error:', e);
      }
    });

    es.onerror = () => {
      setIsConnected(false);
      setError('Connexion SSE perdue — reconnexion dans 10s');
      es.close();
      // Auto-reconnect after 10 seconds
      retryRef.current = setTimeout(() => {
        connect();
      }, 10000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [connect]);

  return { prediction, isConnected, lastReceivedAt, error };
}