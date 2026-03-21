import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketHookOptions {
  url: string;
  onMessage?: (data: unknown) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export function useWebSocket({ url, onMessage, autoReconnect = true, reconnectInterval = 3000 }: WebSocketHookOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (autoReconnect) {
          reconnectTimer.current = setTimeout(connect, reconnectInterval);
        }
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch {
          onMessage?.(event.data);
        }
      };
    } catch {
      if (autoReconnect) {
        reconnectTimer.current = setTimeout(connect, reconnectInterval);
      }
    }
  }, [url, onMessage, autoReconnect, reconnectInterval]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected, ws: wsRef.current };
}
