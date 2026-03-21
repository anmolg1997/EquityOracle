import { useEffect, useRef, useState, useCallback } from 'react';

export function useSSE<T>(url: string | null) {
  const [data, setData] = useState<T[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  const start = useCallback(() => {
    if (!url) return;
    sourceRef.current?.close();

    const source = new EventSource(url);
    sourceRef.current = source;
    setIsStreaming(true);

    source.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as T;
        setData((prev) => [...prev, parsed]);
      } catch {
        setData((prev) => [...prev, event.data as T]);
      }
    };

    source.onerror = () => {
      setIsStreaming(false);
      source.close();
    };
  }, [url]);

  useEffect(() => {
    return () => sourceRef.current?.close();
  }, []);

  const reset = useCallback(() => {
    setData([]);
    sourceRef.current?.close();
    setIsStreaming(false);
  }, []);

  return { data, isStreaming, start, reset };
}
