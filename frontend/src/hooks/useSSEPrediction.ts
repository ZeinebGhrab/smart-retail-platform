// ============================================================
// src/hooks/useSSEPrediction.ts — Connexion SSE temps réel
// au backend Django (GET /api/prediction/stream/)
//
// Le backend rediffuse à ce flux les payloads reçus de N8N via
// POST /api/daily-report/ (event: "llm_report"). Voir
// history/views.py (sse_stream / daily_report) et history/urls.py.
//
// Reconnexion automatique avec backoff en cas de coupure.
// ============================================================

import { useEffect, useRef, useState } from 'react';
import { API_BASE_URL } from '../services/api';
import { PredictionData } from '../types/dashboard.types';

interface UseSSEPredictionResult {
  prediction: PredictionData | null;
  isConnected: boolean;
}

const RECONNECT_DELAY_MS = 5000;

export function useSSEPrediction(): UseSSEPredictionResult {
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      // API_BASE_URL = http://localhost:8000/api → endpoint SSE complet
      const url = `${API_BASE_URL}/prediction/stream/`;
      const es = new EventSource(url);
      sourceRef.current = es;

      es.addEventListener('connected', () => {
        if (cancelled) return;
        setIsConnected(true);
      });

      es.addEventListener('llm_report', (event: MessageEvent) => {
        if (cancelled) return;
        try {
          const data: PredictionData = JSON.parse(event.data);
          setPrediction(data);
        } catch {
          // Payload invalide — ignoré silencieusement
        }
      });

      es.onerror = () => {
        if (cancelled) return;
        setIsConnected(false);
        es.close();
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      sourceRef.current?.close();
    };
  }, []);

  return { prediction, isConnected };
}